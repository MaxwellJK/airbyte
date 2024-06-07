import datetime
from dataclasses import InitVar, dataclass
import requests
from typing import Any, ClassVar, Dict, Iterable, List, Mapping, MutableMapping, Optional, Union
from urllib.parse import urlparse, parse_qs

from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.declarative.datetime.datetime_parser import DatetimeParser
from airbyte_cdk.sources.declarative.decoders.decoder import Decoder
from airbyte_cdk.sources.declarative.decoders.json_decoder import JsonDecoder
from airbyte_cdk.sources.declarative.incremental import Cursor
from airbyte_cdk.sources.declarative.interpolation.interpolated_boolean import InterpolatedBoolean
from airbyte_cdk.sources.declarative.interpolation.interpolated_string import InterpolatedString
from airbyte_cdk.sources.declarative.requesters.paginators.strategies.cursor_pagination_strategy import CursorPaginationStrategy
from airbyte_cdk.sources.declarative.requesters.requester import Requester
from airbyte_cdk.sources.declarative.types import Record, StreamSlice, StreamState, Config
from airbyte_cdk.sources.streams.core import Stream

@dataclass
class PosthogSlicer(Cursor):
    parent_key: str
    parent_stream: Stream
    stream_slice_field: str
    
    parameters: InitVar[Mapping[str, Any]]
    cursor_field: str
    request_cursor_field_after: str
    request_cursor_field_before: str
    config: Config
    cursor_datetime_formats: List[str]    

    DATETIME_FORMAT: ClassVar[str] = "%Y-%m-%dT%H:%M:%S.%fZ"
    DATETIME_FORMAT2: ClassVar[str] = "%Y-%m-%dT%H:%M:%S.%f%z"

    def __post_init__(self, parameters: Mapping[str, Any]):
        self._state = {}
        self.START_DATETIME = self.config['start_date']
        self._parser = DatetimeParser()

    def stream_slices(self) -> Iterable[StreamSlice]:
        yield StreamSlice(partition={}, cursor_slice={self.request_cursor_field_after: self._state.get(self.cursor_field, self.START_DATETIME)})

    def _max_dt_str(self, *args: str) -> Optional[str]:
        new_state_candidates = list(map(lambda x: 
                                            datetime.datetime.strptime(x, self.DATETIME_FORMAT2), 
                                            filter(None, args)
                                        )
                                    )
        if not new_state_candidates:
            return
        max_dt = max(new_state_candidates)
        max_dt = self._parse_to_datetime(max_dt)
        # `.%f` gives us microseconds, we need milliseconds
        (dt, micro) = max_dt.strftime(self.DATETIME_FORMAT).split(".")
        return "%s.%03dZ" % (dt, int(micro[:-5:]) / 1000)

    def set_initial_state(self, stream_state: StreamState) -> None:
        cursor_value = stream_state.get(self.cursor_field)
        if cursor_value:
            self._state[self.cursor_field] = cursor_value

    def close_slice(self, stream_slice: StreamSlice, most_recent_record: Optional[Record]) -> None:
        stream_slice_value = stream_slice.get(self.cursor_field)
        current_state = self._state.get(self.cursor_field)
        record_cursor_value = most_recent_record and most_recent_record[self.cursor_field]
        max_dt = self._max_dt_str(stream_slice_value, current_state, record_cursor_value)
        if not max_dt:
            return
        self._state[self.cursor_field] = max_dt

    def should_be_synced(self, record: Record) -> bool:
        """
        As of 2024-04-24, the expectation is that this method will only be used for semi-incremental and data feed and therefore the
        implementation is irrelevant for PostHog
        """
        return True

    def is_greater_than_or_equal(self, first: Record, second: Record) -> bool:
        """
        Evaluating which record is greater in terms of cursor. This is used to avoid having to capture all the records to close a slice
        """
        first_cursor_value = first.get(self.cursor_field, "")
        second_cursor_value = second.get(self.cursor_field, "")
        if first_cursor_value and second_cursor_value:
            return first_cursor_value >= second_cursor_value
        elif first_cursor_value:
            return True
        else:
            return False

    def _parse_to_datetime(self, datetime_str: str) -> datetime.datetime:
        # return datetime.datetime.strptime(datetime_str, self.DATETIME_FORMAT)
        for datetime_format in self.cursor_datetime_formats + [self.DATETIME_FORMAT] + [self.DATETIME_FORMAT2]:
            try:
                return self._parser.parse(datetime_str, datetime_format)
            except ValueError:
                pass
        raise ValueError(f"No format in {self.cursor_datetime_formats} matching {datetime_str}")

    def get_stream_state(self) -> StreamState:
        return self._state

    def get_request_params(
        self,
        *,
        stream_state: Optional[StreamState] = None,
        stream_slice: Optional[StreamSlice] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        return stream_slice or {}

    def get_request_headers(self, *args, **kwargs) -> Mapping[str, Any]:
        return {}

    def get_request_body_data(self, *args, **kwargs) -> Optional[Union[Mapping, str]]:
        return {}

    def get_request_body_json(self, *args, **kwargs) -> Optional[Mapping]:
        return {}


@dataclass
class PostHogSubstreamSlicer(PosthogSlicer):

    def stream_slices(self) -> Iterable[StreamSlice]:
        for parent_stream_slice in self.parent_stream.stream_slices(
            sync_mode=SyncMode.full_refresh, cursor_field=None, stream_state=self.get_stream_state()
        ):
            for parent_record in self.parent_stream.read_records(
                sync_mode=SyncMode.full_refresh, cursor_field=None, stream_slice=parent_stream_slice, stream_state=None
            ):
                parent_primary_key = parent_record.get(self.parent_key)

                partition = {self.stream_slice_field: parent_primary_key}
                cursor_slice = {
                    self.request_cursor_field_after: self._state.get(str(parent_primary_key), {}).get(self.cursor_field, self.START_DATETIME)
                }

                yield StreamSlice(partition=partition, cursor_slice=cursor_slice)

    def set_initial_state(self, stream_state: StreamState) -> None:
        if self.stream_slice_field in stream_state:
            return
        substream_ids = map(lambda x: str(x), set(stream_state.keys()) | set(self._state.keys()))
        for id_ in substream_ids:
            self._state[id_] = {
                self.cursor_field: self._max_dt_str(
                    stream_state.get(id_, {}).get(self.cursor_field), self._state.get(id_, {}).get(self.cursor_field)
                )
            }

    def close_slice(self, stream_slice: StreamSlice, most_recent_record: Optional[Record]) -> None:
        if most_recent_record:
            substream_id = str(stream_slice[self.stream_slice_field])
            current_state = self._state.get(substream_id, {}).get(self.cursor_field)
            last_state = most_recent_record[self.cursor_field]
            max_dt = self._max_dt_str(last_state, current_state)
            self._state[substream_id] = {self.cursor_field: max_dt}
            return

    def should_be_synced(self, record: Record) -> bool:
        """
        As of 2024-04-24, the expectation is that this method will only be used for semi-incremental and data feed and therefore the
        implementation is irrelevant for PostHog
        """
        return True

    def get_request_params(
        self,
        *,
        stream_state: Optional[StreamState] = None,
        stream_slice: Optional[StreamSlice] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        # ignore other fields in a slice
        return {self.request_cursor_field_after: stream_slice[self.request_cursor_field_after]}
    