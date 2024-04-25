#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

# import datetime
# from dataclasses import InitVar, dataclass
# from typing import Any, ClassVar, Iterable, Mapping, MutableMapping, Optional, Union

# from airbyte_cdk.sources.declarative.incremental import Cursor
# from airbyte_cdk.sources.declarative.retrievers.simple_retriever import SimpleRetriever
# from airbyte_cdk.sources.declarative.stream_slicers import CartesianProductStreamSlicer
# from airbyte_cdk.sources.declarative.types import Record, StreamSlice, StreamState

# from airbyte_cdk.sources.streams.core import Stream
# from airbyte_cdk.models import SyncMode




# @dataclass
# class EventsSimpleRetriever(SimpleRetriever):
#     def __post_init__(self, parameters: Mapping[str, Any]):
#         super().__post_init__(parameters)
#         self.cursor = self.stream_slicer if isinstance(self.stream_slicer, Cursor) else None

#     def request_params(
#         self,
#         stream_state: StreamSlice,
#         stream_slice: Optional[StreamSlice] = None,
#         next_page_token: Optional[Mapping[str, Any]] = None,
#     ) -> MutableMapping[str, Any]:
#         """Events API return records in descendent order (newest first).
#         Default page limit is 100 items.

#         Even though API mentions such pagination params as 'limit' and 'offset', they are actually ignored.
#         Instead, response contains 'next' url with datetime range for next OLDER records, like:

#         response:
#         {
#             "next": "https://app.posthog.com/api/projects/2331/events?after=2021-01-01T00%3A00%3A00.000000Z&before=2021-05-29T16%3A44%3A43.175000%2B00%3A00",
#             "results": [
#                 {id ...},
#                 {id ...},
#             ]
#         }

#         So if next_page_token is set (contains 'after'/'before' params),
#         then stream_slice params ('after'/'before') should be ignored.
#         """

#         if next_page_token:
#             stream_slice = {}

#         return self._get_request_options(
#             stream_slice,
#             next_page_token,
#             self.requester.get_request_params,
#             self.paginator.get_request_params,
#             self.stream_slicer.get_request_params,
#             self.requester.get_authenticator().get_request_body_json,
#         )
    




# @dataclass
# class EventsCartesianProductStreamSlicer(Cursor):
#     """Connector requires support of nested state - each project should have own timestamp value, like:
#     {
#         "project_id1": {
#           "timestamp": "2021-02-01T10:21:35.003000Z"
#         },
#         "project_idX": {
#           "timestamp": "2022-11-17:00:00.000000Z"
#         }
#     }
#     we also have to support old-style (before 0.1.8) states, like:
#     {
#         "timestamp": "2021-17-01T10:21:35.003000Z"
#     }

#     Slicer also produces separate datetime slices for each project
#     """
#     parameters: InitVar[Mapping[str, Any]]
#     cursor_field: str
#     request_cursor_field: str
#     parent_stream: Stream
#     stream_slice_field: str
#     parent_key: str


#     def __post_init__(self, parameters: Mapping[str, Any]):
#         self._cursor = {}
#         self._parameters = parameters

#     def get_stream_state(self) -> Mapping[str, Any]:
#         return self._cursor or {}

#     def set_initial_state(self, stream_state: StreamState) -> None:
#         self._cursor = stream_state

#     def close_slice(self, stream_slice: StreamSlice, most_recent_record: Optional[Record]) -> None:
#         project_id = str(stream_slice.get("project_id", ""))
#         if project_id and most_recent_record:
#             current_cursor_value = self._cursor.get(project_id, {}).get("timestamp", "")
#             new_cursor_value = most_recent_record.get("timestamp", "")

#             self._cursor[project_id] = {"timestamp": max(current_cursor_value, new_cursor_value)}

#     def stream_slices(self) -> Iterable[StreamSlice]:

#         for parent_stream_slice in self.parent_stream.stream_slices(
#             sync_mode=SyncMode.full_refresh, cursor_field=None, stream_state=self.get_stream_state()
#         ):
#             for parent_record in self.parent_stream.read_records(
#                 sync_mode=SyncMode.full_refresh, cursor_field=None, stream_slice=parent_stream_slice, stream_state=None
#             ):
#                 parent_primary_key = parent_record.get(self.parent_key)
#                 print(parent_primary_key)

#                 partition = {self.stream_slice_field: parent_primary_key}
#                 cursor_slice = {
#                     self.request_cursor_field: self._state.get(str(parent_primary_key), {}).get(self.cursor_field, self.START_DATETIME)
#                 }

#                 yield StreamSlice(partition=partition, cursor_slice=cursor_slice)


#     # def stream_slices(self) -> Iterable[StreamSlice]:
#     #     """Since each project has its own state, then we need to have a separate
#     #     datetime slices for each project
#     #     """

#     #     slices = []

#     #     project_slicer, datetime_slicer = self.stream_slicers
#     #     # datetime_slicer = DatetimeBasedCursor(start_datetime=, cursor_field, datetime_format, config, parameters)
#     #     # project_slicer = self.stream_slicers

#     #     print(f'project_slicer {project_slicer}')
#     #     print(f'datetime_slicer {datetime_slicer}')

#     #     # support of old style state: it contains only a single 'timestamp' field
#     #     old_style_state = self._cursor if "timestamp" in self._cursor else {}

#     #     for project_slice in project_slicer.stream_slices():
#     #         project_id = str(project_slice.get("project_id", ""))
#     #         print(f'project_slice {project_slice}')
#     #         print(f'project_id {project_id}')

#     #         # use old_style_state if state does not contain states for each project
#     #         project_state = self._cursor.get(project_id, {}) or old_style_state

#     #         print(f'project_state {project_state}')

#     #         # Each project should have own datetime slices depends on its state
#     #         datetime_slicer.set_initial_state(project_state)
#     #         project_datetime_slices = datetime_slicer.stream_slices()

#     #         print(f'project_datetime_slices {project_datetime_slices}')

#     #         # fix date ranges: start_time of next slice must be equal to end_time of previous slice
#     #         if project_datetime_slices and project_state:
#     #             project_datetime_slices[0]["start_time"] = project_state["timestamp"]

#     #         print(f'project_datetime_slices_project_timestamp {project_datetime_slices}')

#     #         for i, datetime_slice in enumerate(project_datetime_slices[1:], start=1):
#     #             print(i)
#     #             print(datetime_slice)
#     #             print(project_datetime_slices[i - 1]["end_time"])
#     #             datetime_slice["start_time"] = project_datetime_slices[i - 1]["end_time"]

#     #         # Add project id to each slice
#     #         for datetime_slice in project_datetime_slices:
#     #             datetime_slice["project_id"] = project_id

#     #         slices.extend(project_datetime_slices)

#     #     return slices

#     def should_be_synced(self, record: Record) -> bool:
#         """
#         As of 2024-04-24, the expectation is that this method will only be used for semi-incremental and data feed and therefore the
#         implementation is irrelevant for posthog
#         """
#         return True

#     def is_greater_than_or_equal(self, first: Record, second: Record) -> bool:
#         """
#         Evaluating which record is greater in terms of cursor. This is used to avoid having to capture all the records to close a slice
#         """
#         first_cursor_value = first.get("timestamp")
#         second_cursor_value = second.get("timestamp")
#         if first_cursor_value and second_cursor_value:
#             return first_cursor_value >= second_cursor_value
#         elif first_cursor_value:
#             return True
#         else:
#             return False










# from dataclasses import InitVar, dataclass
# from typing import Any, List, Mapping, Optional, Union

# import requests
# from airbyte_cdk.sources.declarative.decoders.decoder import Decoder
# from airbyte_cdk.sources.declarative.decoders.json_decoder import JsonDecoder
# from airbyte_cdk.sources.declarative.interpolation.interpolated_boolean import InterpolatedBoolean
# from airbyte_cdk.sources.declarative.interpolation.interpolated_string import InterpolatedString
# from airbyte_cdk.sources.declarative.requesters.paginators.strategies.pagination_strategy import PaginationStrategy
# from airbyte_cdk.sources.declarative.types import Config

# @dataclass
# class MyCursorPaginationStrategy(PaginationStrategy):
#     """
#     Pagination strategy that evaluates an interpolated string to define the next page token

#     Attributes:
#         page_size (Optional[int]): the number of records to request
#         cursor_value (Union[InterpolatedString, str]): template string evaluating to the cursor value
#         config (Config): connection config
#         stop_condition (Optional[InterpolatedBoolean]): template string evaluating when to stop paginating
#         decoder (Decoder): decoder to decode the response
#     """

#     cursor_value: Union[InterpolatedString, str]
#     config: Config
#     parameters: InitVar[Mapping[str, Any]]
#     page_size: Optional[int] = None
#     stop_condition: Optional[Union[InterpolatedBoolean, str]] = None
#     decoder: Decoder = JsonDecoder(parameters={})

#     def __post_init__(self, parameters: Mapping[str, Any]):
#         print('in __post_init__')

#         if isinstance(self.cursor_value, str):
#             self.cursor_value = InterpolatedString.create(self.cursor_value, parameters=parameters)
#         if isinstance(self.stop_condition, str):
#             self.stop_condition = InterpolatedBoolean(condition=self.stop_condition, parameters=parameters)

#     @property
#     def initial_token(self) -> Optional[Any]:
#         return None

#     def next_page_token(self, response: requests.Response, last_records: List[Mapping[str, Any]]) -> Optional[Any]:
#         decoded_response = self.decoder.decode(response)

#         # print('in next_page_token')
#         # print(response.json())
#         # print(response.url)
        
#         # The default way that link is presented in requests.Response is a string of various links (last, next, etc). This
#         # is not indexable or useful for parsing the cursor, so we replace it with the link dictionary from response.links
#         headers = response.headers
#         headers["link"] = response.links


#         if self.stop_condition:
#             should_stop = self.stop_condition.eval(self.config, response=decoded_response, headers=headers, last_records=last_records)
#             if should_stop:
#                 return None

#         token = self.cursor_value.eval(config=self.config, last_records=last_records, response=decoded_response, headers=headers)
        
#         return token if token else None

#     def reset(self):
#         # No state to reset
#         pass

#     def get_page_size(self) -> Optional[int]:
#         return self.page_size















# #
# # Copyright (c) 2023 Airbyte, Inc., all rights reserved.
# #

# import datetime
# from dataclasses import InitVar, dataclass, field
# from typing import Any, Iterable, List, Mapping, Optional, Union

# from airbyte_cdk.models import AirbyteLogMessage, AirbyteMessage, Level, Type
# from airbyte_cdk.sources.declarative.datetime.datetime_parser import DatetimeParser
# from airbyte_cdk.sources.declarative.datetime.min_max_datetime import MinMaxDatetime
# from airbyte_cdk.sources.declarative.incremental.cursor import Cursor
# from airbyte_cdk.sources.declarative.interpolation.interpolated_string import InterpolatedString
# from airbyte_cdk.sources.declarative.interpolation.jinja import JinjaInterpolation
# from airbyte_cdk.sources.declarative.requesters.request_option import RequestOption, RequestOptionType
# from airbyte_cdk.sources.declarative.types import Config, Record, StreamSlice, StreamState
# from airbyte_cdk.sources.message import MessageRepository
# from isodate import Duration, parse_duration


# @dataclass
# class MyDatetimeBasedCursor(Cursor):
#     """
#     Slices the stream over a datetime range and create a state with format {<cursor_field>: <datetime> }

#     Given a start time, end time, a step function, and an optional lookback window,
#     the stream slicer will partition the date range from start time - lookback window to end time.

#     The step function is defined as a string of the form ISO8601 duration

#     The timestamp format accepts the same format codes as datetime.strfptime, which are
#     all the format codes required by the 1989 C standard.
#     Full list of accepted format codes: https://man7.org/linux/man-pages/man3/strftime.3.html

#     Attributes:
#         start_datetime (Union[MinMaxDatetime, str]): the datetime that determines the earliest record that should be synced
#         end_datetime (Optional[Union[MinMaxDatetime, str]]): the datetime that determines the last record that should be synced
#         cursor_field (Union[InterpolatedString, str]): record's cursor field
#         datetime_format (str): format of the datetime
#         step (Optional[str]): size of the timewindow (ISO8601 duration)
#         cursor_granularity (Optional[str]): smallest increment the datetime_format has (ISO 8601 duration) that will be used to ensure that the start of a slice does not overlap with the end of the previous one
#         config (Config): connection config
#         start_time_option (Optional[RequestOption]): request option for start time
#         end_time_option (Optional[RequestOption]): request option for end time
#         partition_field_start (Optional[str]): partition start time field
#         partition_field_end (Optional[str]): stream slice end time field
#         lookback_window (Optional[InterpolatedString]): how many days before start_datetime to read data for (ISO8601 duration)
#     """

#     start_datetime: Union[MinMaxDatetime, str]
#     cursor_field: Union[InterpolatedString, str]
#     datetime_format: str
#     config: Config
#     parameters: InitVar[Mapping[str, Any]]
#     _cursor: Optional[str] = field(repr=False, default=None)  # tracks current datetime
#     end_datetime: Optional[Union[MinMaxDatetime, str]] = None
#     step: Optional[Union[InterpolatedString, str]] = None
#     cursor_granularity: Optional[str] = None
#     start_time_option: Optional[RequestOption] = None
#     end_time_option: Optional[RequestOption] = None
#     partition_field_start: Optional[str] = None
#     partition_field_end: Optional[str] = None
#     lookback_window: Optional[Union[InterpolatedString, str]] = None
#     message_repository: Optional[MessageRepository] = None
#     cursor_datetime_formats: List[str] = field(default_factory=lambda: [])

#     def __post_init__(self, parameters: Mapping[str, Any]) -> None:
#         print("in __post_init__ in MyDatetimeBasedCursor")
#         if (self.step and not self.cursor_granularity) or (not self.step and self.cursor_granularity):
#             raise ValueError(
#                 f"If step is defined, cursor_granularity should be as well and vice-versa. "
#                 f"Right now, step is `{self.step}` and cursor_granularity is `{self.cursor_granularity}`"
#             )
#         if not isinstance(self.start_datetime, MinMaxDatetime):
#             self.start_datetime = MinMaxDatetime(self.start_datetime, parameters)
#         if self.end_datetime and not isinstance(self.end_datetime, MinMaxDatetime):
#             self.end_datetime = MinMaxDatetime(self.end_datetime, parameters)

#         self._timezone = datetime.timezone.utc
#         self._interpolation = JinjaInterpolation()

#         self._step = (
#             self._parse_timedelta(InterpolatedString.create(self.step, parameters=parameters).eval(self.config))
#             if self.step
#             else datetime.timedelta.max
#         )
#         self._cursor_granularity = self._parse_timedelta(self.cursor_granularity)
#         self.cursor_field = InterpolatedString.create(self.cursor_field, parameters=parameters)
#         self.lookback_window = InterpolatedString.create(self.lookback_window, parameters=parameters)
#         self.partition_field_start = InterpolatedString.create(self.partition_field_start or "start_time", parameters=parameters)
#         self.partition_field_end = InterpolatedString.create(self.partition_field_end or "end_time", parameters=parameters)
#         self._parser = DatetimeParser()
#         self._parameters = parameters

#         # If datetime format is not specified then start/end datetime should inherit it from the stream slicer
#         if not self.start_datetime.datetime_format:
#             self.start_datetime.datetime_format = self.datetime_format
#         if self.end_datetime and not self.end_datetime.datetime_format:
#             self.end_datetime.datetime_format = self.datetime_format

#         if not self.cursor_datetime_formats:
#             self.cursor_datetime_formats = [self.datetime_format]

#     def get_stream_state(self) -> StreamState:
#         return {self.cursor_field.eval(self.config): self._cursor} if self._cursor else {}

#     def set_initial_state(self, stream_state: StreamState) -> None:
#         """
#         Cursors are not initialized with their state. As state is needed in order to function properly, this method should be called
#         before calling anything else

#         :param stream_state: The state of the stream as returned by get_stream_state
#         """
#         self._cursor = stream_state.get(self.cursor_field.eval(self.config)) if stream_state else None

#     def close_slice(self, stream_slice: StreamSlice, most_recent_record: Optional[Record]) -> None:
#         last_record_cursor_value = most_recent_record.get(self.cursor_field.eval(self.config)) if most_recent_record else None
#         stream_slice_value_end = stream_slice.get(self.partition_field_end.eval(self.config))
#         cursor_value_str_by_cursor_value_datetime = dict(
#             map(
#                 # we need to ensure the cursor value is preserved as is in the state else the CATs might complain of something like
#                 # 2023-01-04T17:30:19.000Z' <= '2023-01-04T17:30:19.000000Z'
#                 lambda datetime_str: (self.parse_date(datetime_str), datetime_str),
#                 filter(lambda item: item, [self._cursor, last_record_cursor_value, stream_slice_value_end]),
#             )
#         )
#         self._cursor = (
#             cursor_value_str_by_cursor_value_datetime[max(cursor_value_str_by_cursor_value_datetime.keys())]
#             if cursor_value_str_by_cursor_value_datetime
#             else None
#         )

#     def stream_slices(self) -> Iterable[StreamSlice]:
#         """
#         Partition the daterange into slices of size = step.

#         The start of the window is the minimum datetime between start_datetime - lookback_window and the stream_state's datetime
#         The end of the window is the minimum datetime between the start of the window and end_datetime.

#         :return:
#         """
#         end_datetime = self._select_best_end_datetime()
#         start_datetime = self._calculate_earliest_possible_value(self._select_best_end_datetime())
#         return self._partition_daterange(start_datetime, end_datetime, self._step)

#     def _calculate_earliest_possible_value(self, end_datetime: datetime.datetime) -> datetime.datetime:
#         lookback_delta = self._parse_timedelta(self.lookback_window.eval(self.config) if self.lookback_window else "P0D")
#         earliest_possible_start_datetime = min(self.start_datetime.get_datetime(self.config), end_datetime)
#         cursor_datetime = self._calculate_cursor_datetime_from_state(self.get_stream_state())
#         return max(earliest_possible_start_datetime, cursor_datetime) - lookback_delta

#     def _select_best_end_datetime(self) -> datetime.datetime:        
#         now = datetime.datetime.now(tz=self._timezone)
#         if not self.end_datetime:
#             return now

#         return min(self.end_datetime.get_datetime(self.config), now)

#     def _calculate_cursor_datetime_from_state(self, stream_state: Mapping[str, Any]) -> datetime.datetime:
#         if self.cursor_field.eval(self.config, stream_state=stream_state) in stream_state:
#             return self.parse_date(stream_state[self.cursor_field.eval(self.config)])
#         return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

#     def _format_datetime(self, dt: datetime.datetime) -> str:
#         return self._parser.format(dt, self.datetime_format)

#     def _partition_daterange(self, start: datetime.datetime, end: datetime.datetime, step: Union[datetime.timedelta, Duration]):
#         start_field = self.partition_field_start.eval(self.config)
#         end_field = self.partition_field_end.eval(self.config)
#         dates = []
#         while start <= end:
#             next_start = self._evaluate_next_start_date_safely(start, step)
#             end_date = self._get_date(next_start - self._cursor_granularity, end, min)
#             dates.append({start_field: self._format_datetime(start), end_field: self._format_datetime(end_date)})
#             start = next_start
#         return dates

#     def _evaluate_next_start_date_safely(self, start, step):
#         """
#         Given that we set the default step at datetime.timedelta.max, we will generate an OverflowError when evaluating the next start_date
#         This method assumes that users would never enter a step that would generate an overflow. Given that would be the case, the code
#         would have broken anyway.
#         """
#         try:
#             return start + step
#         except OverflowError:
#             return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)

#     def _get_date(self, cursor_value, default_date: datetime.datetime, comparator) -> datetime.datetime:
#         cursor_date = cursor_value or default_date
#         return comparator(cursor_date, default_date)

#     def parse_date(self, date: str) -> datetime.datetime:
#         for datetime_format in self.cursor_datetime_formats + [self.datetime_format]:
#             try:
#                 return self._parser.parse(date, datetime_format)
#             except ValueError:
#                 pass
#         raise ValueError(f"No format in {self.cursor_datetime_formats} matching {date}")

#     @classmethod
#     def _parse_timedelta(cls, time_str) -> Union[datetime.timedelta, Duration]:
#         """
#         :return Parses an ISO 8601 durations into datetime.timedelta or Duration objects.
#         """
#         if not time_str:
#             return datetime.timedelta(0)
#         return parse_duration(time_str)

#     def get_request_params(
#         self,
#         *,
#         stream_state: Optional[StreamState] = None,
#         stream_slice: Optional[StreamSlice] = None,
#         next_page_token: Optional[Mapping[str, Any]] = None,
#     ) -> Mapping[str, Any]:
#         return self._get_request_options(RequestOptionType.request_parameter, stream_slice)

#     def get_request_headers(
#         self,
#         *,
#         stream_state: Optional[StreamState] = None,
#         stream_slice: Optional[StreamSlice] = None,
#         next_page_token: Optional[Mapping[str, Any]] = None,
#     ) -> Mapping[str, Any]:
#         return self._get_request_options(RequestOptionType.header, stream_slice)

#     def get_request_body_data(
#         self,
#         *,
#         stream_state: Optional[StreamState] = None,
#         stream_slice: Optional[StreamSlice] = None,
#         next_page_token: Optional[Mapping[str, Any]] = None,
#     ) -> Mapping[str, Any]:
#         return self._get_request_options(RequestOptionType.body_data, stream_slice)

#     def get_request_body_json(
#         self,
#         *,
#         stream_state: Optional[StreamState] = None,
#         stream_slice: Optional[StreamSlice] = None,
#         next_page_token: Optional[Mapping[str, Any]] = None,
#     ) -> Mapping[str, Any]:
#         return self._get_request_options(RequestOptionType.body_json, stream_slice)

#     def request_kwargs(self) -> Mapping[str, Any]:
#         # Never update kwargs
#         return {}

#     def _get_request_options(self, option_type: RequestOptionType, stream_slice: StreamSlice):
#         options = {}
#         if self.start_time_option and self.start_time_option.inject_into == option_type:
#             options[self.start_time_option.field_name] = stream_slice.get(self.partition_field_start.eval(self.config))
#         if self.end_time_option and self.end_time_option.inject_into == option_type:
#             options[self.end_time_option.field_name] = stream_slice.get(self.partition_field_end.eval(self.config))
#         return options

#     def should_be_synced(self, record: Record) -> bool:
#         cursor_field = self.cursor_field.eval(self.config)
#         record_cursor_value = record.get(cursor_field)
#         if not record_cursor_value:
#             self._send_log(
#                 Level.WARN,
#                 f"Could not find cursor field `{cursor_field}` in record. The incremental sync will assume it needs to be synced",
#             )
#             return True

#         latest_possible_cursor_value = self._select_best_end_datetime()
#         earliest_possible_cursor_value = self._calculate_earliest_possible_value(latest_possible_cursor_value)
#         return earliest_possible_cursor_value <= self.parse_date(record_cursor_value) <= latest_possible_cursor_value

#     def _send_log(self, level: Level, message: str) -> None:
#         if self.message_repository:
#             self.message_repository.emit_message(
#                 AirbyteMessage(
#                     type=Type.LOG,
#                     log=AirbyteLogMessage(level=level, message=message),
#                 )
#             )

#     def is_greater_than_or_equal(self, first: Record, second: Record) -> bool:
#         cursor_field = self.cursor_field.eval(self.config)
#         first_cursor_value = first.get(cursor_field)
#         second_cursor_value = second.get(cursor_field)
#         if first_cursor_value and second_cursor_value:
#             return self.parse_date(first_cursor_value) >= self.parse_date(second_cursor_value)
#         elif first_cursor_value:
#             return True
#         else:
#             return False


import datetime
from dataclasses import InitVar, dataclass
from typing import Any, ClassVar, Iterable, Mapping, MutableMapping, Optional, Union

from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.declarative.incremental import Cursor
from airbyte_cdk.sources.declarative.types import Record, StreamSlice, StreamState, Config
from airbyte_cdk.sources.streams.core import Stream
from airbyte_cdk.sources.declarative.datetime.min_max_datetime import MinMaxDatetime



@dataclass
class PosthogSlicer(Cursor):
    parameters: InitVar[Mapping[str, Any]]
    cursor_field: str
    request_cursor_field_after: str
    request_cursor_field_before: str
    config: Config


    START_DATETIME: ClassVar[str] = "1970-01-01T00:00:00.000Z"
    DATETIME_FORMAT: ClassVar[str] = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __post_init__(self, parameters: Mapping[str, Any]):
        self._state = {}
        self.START_DATETIME = self.config['start_date']

    def stream_slices(self) -> Iterable[StreamSlice]:
        yield StreamSlice(partition={}, cursor_slice={self.request_cursor_field_after: self._state.get(self.cursor_field, self.START_DATETIME)})

    def _max_dt_str(self, *args: str) -> Optional[str]:
        new_state_candidates = list(map(lambda x: datetime.datetime.strptime(x, self.DATETIME_FORMAT), filter(None, args)))
        if not new_state_candidates:
            return
        max_dt = max(new_state_candidates)
        # `.%f` gives us microseconds, we need milliseconds
        (dt, micro) = max_dt.strftime(self.DATETIME_FORMAT).split(".")
        return "%s.%03dZ" % (dt, int(micro[:-1:]) / 1000)

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
        return datetime.datetime.strptime(datetime_str, self.DATETIME_FORMAT)

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
    parent_stream: Stream
    stream_slice_field: str
    parent_key: str


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
