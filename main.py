from dataclasses import dataclass
import time
from enum import Enum, auto
import random
import PySimpleGUI as sg


class TestModes(Enum):
    HALF_MIN = '1/2 min', 30
    ONE_MIN = '1 min', 60
    TWO_MIN = '2 min', 120
    ENDLESS = 'Endless', 0

    def __str__(self):
        return self.value[0]

    def __int__(self):
        return self.value[1]

    @staticmethod
    def get_object_by_str(s: str):
        for x in TestModes:
            if str(x) == s:
                return x

    @staticmethod
    def mode_list() -> list[str]:
        return [mode.value[0] for mode in TestModes]


class WindowElements(Enum):
    INPUT = auto()
    OUTPUT = auto()
    ENGLISH_BTN = auto()
    RUSSIAN_RTN = auto()
    TEST_PROGRESS_INDICATOR = auto()
    COUNTER = auto()
    TIME_SETTER = auto()


# TODO: prettier in
WINDOW_LAYOUT = [
    [sg.Button('English', key=WindowElements.ENGLISH_BTN),
     sg.Button('Russian', key=WindowElements.RUSSIAN_RTN),
     sg.Text(' ', key=WindowElements.TEST_PROGRESS_INDICATOR),  # TODO: change to ProgressBar
     sg.Text('Counter: 0', key=WindowElements.COUNTER),
     sg.DropDown(TestModes.mode_list(), default_value=TestModes.ONE_MIN,
                 enable_events=True, key=WindowElements.TIME_SETTER),
     sg.Text('Info', tooltip='Select mode and enter "! " to start test', background_color='dark gray')],
    [sg.Multiline(size=(50, 1), key=WindowElements.OUTPUT,
                  no_scrollbar=True, disabled=True,
                  default_text='Chose mode above and enter "! " to start')],
    [sg.Input(size=(50, 1), key=WindowElements.INPUT, enable_events=True)]
]


class Dictionary:
    def __init__(self, filename: str = None):
        self.words: tuple[str] = ()
        self.source = filename

        if filename is not None:
            self.open_file(filename)

    def open_file(self, filename: str):
        self.source = filename
        temp_list: list[str] = []
        for line in open(filename):
            temp_list.append(line.split()[2])

        self.words = tuple(temp_list)

    def random_word(self, is_normalized=True) -> str:
        if is_normalized:
            rand = int(min(abs(random.expovariate(-3) * len(self.words)), len(self.words)-1))
            # print(f'{rand}, {len(self.words)}, {self.words[rand]}')

            return self.words[rand]

        return random.choice(self.words)


@dataclass
class LogEntry:
    dict_name: str
    time_: int
    hits: int
    misses: int

    def __str__(self):
        return f'"{self.dict_name}", {self.time_}, {self.hits}, {self.misses}\n'


class ProgressLogger:
    def __init__(self, filename: str = None):
        self.filename = filename if filename is not None else 'progress.log'
        if not self.filename.endswith('.log'):
            self.filename += '.log'

        self.log_buffer = []

    def log(self, l: LogEntry):
        self.log_buffer.append(l)

    def flush(self):
        with open(self.filename, 'a') as file:
            for log in self.log_buffer:
                file.write(str(log))


class Testing:
    ENDLESS_MODE_UPD_PERIOD = 30

    def __init__(self):
        self.test_dictionary: Dictionary = None
        self.is_test_running = False
        self.test_start_time: float = 0
        self.target_word: str = ''
        self.scored: int = 0
        self.missed: int = 0
        self.timeout_sec: int = 1

    def setup_test(self, test_dictionary: Dictionary, time_sec: int = 60) -> str | None:
        self.test_dictionary = test_dictionary
        self.target_word = self.test_dictionary.random_word()
        self.scored = 0
        self.missed = 0
        self.timeout_sec = time_sec
        return self.target_word

    def check_word(self, entered_word: str) -> bool:
        if not self.is_test_running:
            if entered_word.lower() == '! ':
                self.scored = 0
                self.missed = 0
                self.is_test_running = True
                self.test_start_time = time.perf_counter()
                return True
            return False

        if not entered_word.endswith(' '):
            return False

        if entered_word[:-1] == self.target_word:
            print(f'Score {self.scored}!')
            self.scored += 1
        else:
            print(f'Miss {self.missed}!')
            self.missed += 1

        self.target_word = self.test_dictionary.random_word()
        return True

    def get_target_line(self) -> str:
        return self.target_word

    def is_timeout(self) -> bool:
        if not self.is_test_running:
            return False

        period = self.ENDLESS_MODE_UPD_PERIOD if self.timeout_sec == 0 else self.timeout_sec

        if time.perf_counter() - self.test_start_time < period:
            return False

        if self.timeout_sec != 0:
            print('TIME IS OUT!')
            self.is_test_running = 0
            return True

        self.test_start_time = time.perf_counter()
        return True

    def get_results_log(self) -> LogEntry:
        period = self.ENDLESS_MODE_UPD_PERIOD if self.timeout_sec == 0 else self.timeout_sec
        return LogEntry(self.test_dictionary.source, period, self.scored, self.missed)

    def get_result_str(self):
        period = self.ENDLESS_MODE_UPD_PERIOD if self.timeout_sec == 0 else self.timeout_sec
        return f'"{self.test_dictionary.source}", {period}, {self.scored}, {self.missed}'


def event_loop(window: sg.Window, element_to_dict: dict[WindowElements: Dictionary]):
    testing = Testing()
    print(type(window.find_element(WindowElements.TIME_SETTER).get()))
    active_dict = element_to_dict[WindowElements.ENGLISH_BTN]

    progress_logger = ProgressLogger()

    while True:
        event, values = window.read(0)
        if event == "__TIMEOUT__":
            if testing.is_timeout():
                print(testing.get_result_str())
                score = testing.scored
                window.find_element(WindowElements.COUNTER).update(f'Counter: {score}')

                progress_logger.log(testing.get_results_log())

            continue

        elif event in (None, 'Exit', "Close"):
            progress_logger.flush()
            break

        elif event in (WindowElements.ENGLISH_BTN, WindowElements.RUSSIAN_RTN):
            active_dict = element_to_dict[event]
            time_setter = values[WindowElements.TIME_SETTER]
            time_mode = int(TestModes.get_object_by_str(time_setter))

            te = testing.setup_test(active_dict, time_mode)
            window.find_element(WindowElements.OUTPUT).update(te)

        elif event is WindowElements.INPUT:
            if testing.check_word(values[event]):
                window.find_element(WindowElements.INPUT).update('')
                window.find_element(WindowElements.OUTPUT).update(testing.get_target_line())
                window.find_element(WindowElements.COUNTER).update(f'Counter: {testing.scored}')

        elif event is WindowElements.TIME_SETTER:
            time_setter = values[WindowElements.TIME_SETTER]
            time_mode = int(TestModes.get_object_by_str(time_setter))

            te = testing.setup_test(active_dict, time_mode)
            window.find_element(WindowElements.OUTPUT).update(te)

        else:
            print(type(event), event)


def main():
    english_dict = Dictionary('english.num')
    russian_dict = Dictionary('russian.num')

    print('---')
    window = sg.Window('Speed Typing v0.2', WINDOW_LAYOUT, finalize=True, size=(600, 150), scaling=2)
    print('---')

    element_to_dict = {WindowElements.ENGLISH_BTN: english_dict, WindowElements.RUSSIAN_RTN: russian_dict}
    event_loop(window, element_to_dict)


if __name__ == '__main__':
    main()
