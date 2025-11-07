import re
from collections import UserDict
from datetime import date, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple


PHONE_REGEX = re.compile(r"\d{10}")


class Command(str, Enum):
    ADD = "add"
    CHANGE = "change"
    PHONE = "phone"
    ALL = "all"
    ADD_BIRTHDAY = "add-birthday"
    SHOW_BIRTHDAY = "show-birthday"
    BIRTHDAYS = "birthdays"
    HELLO = "hello"
    HELP = "help"
    CLOSE = "close"
    EXIT = "exit"


COMMAND_TEMPLATES: Dict[Command, str] = {
    Command.ADD: "add <name> <10-digit phone>",
    Command.CHANGE: "change <name> <old-phone> <new-phone>",
    Command.PHONE: "phone <name>",
    Command.ALL: "all",
    Command.ADD_BIRTHDAY: "add-birthday <name> <DD.MM.YYYY>",
    Command.SHOW_BIRTHDAY: "show-birthday <name>",
    Command.BIRTHDAYS: "birthdays",
    Command.HELLO: "hello",
    Command.HELP: "help",
    Command.CLOSE: "close",
    Command.EXIT: "exit",
}


class Field:
    def __init__(self, value: Any) -> None:
        self._value: Any = None
        self.value = value

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    @Field.value.setter
    def value(self, name: str) -> None:
        if not name:
            raise ValueError("Name cannot be empty.")
        self._value = name


class Phone(Field):
    @Field.value.setter
    def value(self, new_phone_number: str) -> None:
        if not PHONE_REGEX.fullmatch(str(new_phone_number)):
            raise ValueError("Phone number must contain exactly 10 digits.")
        self._value = new_phone_number


class Birthday(Field):
    @property
    def value(self) -> Optional[datetime]:
        return self._value

    @Field.value.setter
    def value(self, value: Optional[Any]) -> None:
        if value is None:
            self._value = None
            return

        if isinstance(value, datetime):
            self._value = value
            return

        if isinstance(value, str):
            try:
                parsed_date = datetime.strptime(value, "%d.%m.%Y")
            except ValueError as error:
                raise ValueError("Invalid date format. Use DD.MM.YYYY") from error
            self._value = parsed_date
            return

        raise ValueError("Birthday must be a datetime instance or string in DD.MM.YYYY format.")

    def __str__(self) -> str:
        if not self.value:
            return ""
        return self.value.strftime("%d.%m.%Y")


class Record:
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Optional[Birthday] = None

    def add_phone(self, phone: str) -> None:
        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str) -> None:
        phone_obj = self.find_phone(phone)
        if not phone_obj:
            raise ValueError("Phone number not found.")
        self.phones.remove(phone_obj)

    def edit_phone(self, existing_phone_number: str, new_phone_number: str) -> None:
        phone_to_edit = self.find_phone(existing_phone_number)
        if not phone_to_edit:
            raise ValueError("Phone number to edit not found.")
        self.phones[self.phones.index(phone_to_edit)] = Phone(new_phone_number)

    def find_phone(self, phone: str) -> Optional[Phone]:
        for phone_obj in self.phones:
            if phone_obj.value == phone:
                return phone_obj
        return None

    def add_birthday(self, birthday: str) -> None:
        self.birthday = Birthday(birthday)

    def days_to_birthday(self) -> Optional[int]:
        if not self.birthday or self.birthday.value is None:
            return None
        today = datetime.today().date()
        next_birthday = self.birthday.value.date().replace(year=today.year)
        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)
        return (next_birthday - today).days

    def __str__(self) -> str:
        phones = "; ".join(phone.value for phone in self.phones)
        birthday_str = f", birthday: {self.birthday}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{birthday_str}"


class AddressBook(UserDict):
    data: Dict[str, Record]

    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        return self.data.get(name)

    def delete(self, name: str) -> None:
        if name in self.data:
            del self.data[name]
        else:
            raise KeyError(f"Record with name '{name}' not found.")


def get_upcoming_birthdays(users: List[Dict[str, str]]) -> List[Dict[str, str]]:
    today: date = datetime.today().date()
    upcoming_birthdays: List[Dict[str, str]] = []

    for user in users:
        birthday_date = datetime.strptime(user["birthday"], "%Y.%m.%d").date()

        birthday_this_year = birthday_date.replace(year=today.year)

        if birthday_this_year < today:
            birthday_this_year = birthday_this_year.replace(year=today.year + 1)

        delta_days = (birthday_this_year - today).days

        is_upcoming_birthday = 0 <= delta_days < 7

        if is_upcoming_birthday:
            congratulation_date = birthday_this_year

            if congratulation_date.weekday() >= 5:
                days_to_monday = 7 - congratulation_date.weekday()
                congratulation_date += timedelta(days=days_to_monday)

            upcoming_birthdays.append(
                {
                    "name": user["name"],
                    "congratulation_date": congratulation_date.strftime("%Y.%m.%d"),
                }
            )

    return upcoming_birthdays


def input_error(func: Callable[..., str]) -> Callable[..., str]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except (ValueError, IndexError) as error:
            return str(error)
        except KeyError as error:
            return str(error)

    return wrapper


def parse_input(user_input: str) -> Tuple[Optional[Command], List[str], Optional[str]]:
    parts = user_input.strip().split()
    if not parts:
        return None, [], None
    original_command = parts[0]
    command_str = original_command.lower()
    try:
        command = Command(command_str)
    except ValueError:
        command = None
    return command, parts[1:], original_command


def _command_usage_summary() -> str:
    return "\n".join(f"- {template}" for template in COMMAND_TEMPLATES.values())


def format_unknown_command_message(raw_command: Optional[str]) -> str:
    prefix = (
        f"Unknown command '{raw_command}'."
        if raw_command
        else "Unknown command."
    )
    return f"{prefix}\nUse one of the following patterns:\n{_command_usage_summary()}"


@input_error
def add_contact(args: List[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError(f"Missing arguments. Usage: {COMMAND_TEMPLATES[Command.ADD]}")
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_phone(args: List[str], book: AddressBook) -> str:
    if len(args) < 3:
        raise ValueError(f"Missing arguments. Usage: {COMMAND_TEMPLATES[Command.CHANGE]}")
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError("Contact not found.")
    record.edit_phone(old_phone, new_phone)
    return "Phone number updated."


@input_error
def show_phone(args: List[str], book: AddressBook) -> str:
    if not args:
        raise ValueError(f"Missing contact name. Usage: {COMMAND_TEMPLATES[Command.PHONE]}")
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError("Contact not found.")
    if not record.phones:
        return "No phone numbers for this contact."
    return "; ".join(phone.value for phone in record.phones)


@input_error
def show_all(args: List[str], book: AddressBook) -> str:
    if args:
        raise ValueError(f"No extra arguments expected. Usage: {COMMAND_TEMPLATES[Command.ALL]}")
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args: List[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError(f"Missing arguments. Usage: {COMMAND_TEMPLATES[Command.ADD_BIRTHDAY]}")
    name, birthday_str, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
    record.add_birthday(birthday_str)
    return "Birthday added."


@input_error
def show_birthday(args: List[str], book: AddressBook) -> str:
    if not args:
        raise ValueError(f"Missing contact name. Usage: {COMMAND_TEMPLATES[Command.SHOW_BIRTHDAY]}")
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError("Contact not found.")
    if not record.birthday or record.birthday.value is None:
        return "Birthday not set."
    return record.birthday.value.strftime("%d.%m.%Y")


@input_error
def birthdays(args: List[str], book: AddressBook) -> str:
    if args:
        raise ValueError(f"No extra arguments expected. Usage: {COMMAND_TEMPLATES[Command.BIRTHDAYS]}")
    today: date = datetime.today().date()
    upcoming: Dict[date, List[str]] = {}
    for record in book.data.values():
        if not record.birthday or record.birthday.value is None:
            continue
        birthday_date = record.birthday.value.date()
        next_birthday = birthday_date.replace(year=today.year)
        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)
        days_until = (next_birthday - today).days
        if 0 <= days_until < 7:
            congratulation_date = next_birthday
            if congratulation_date.weekday() >= 5:
                congratulation_date += timedelta(days=7 - congratulation_date.weekday())
            upcoming.setdefault(congratulation_date, []).append(record.name.value)

    if not upcoming:
        return "No upcoming birthdays."

    lines: List[str] = []
    for day in sorted(upcoming):
        names = ", ".join(sorted(upcoming[day]))
        lines.append(f"{day.strftime('%d.%m.%Y')}: {names}")
    return "\n".join(lines)


@input_error
def show_commands(args: List[str], _: AddressBook) -> str:
    if args:
        raise ValueError(f"No extra arguments expected. Usage: {COMMAND_TEMPLATES[Command.HELP]}")
    return "Available commands:\n" + _command_usage_summary()


def main() -> None:
    book: AddressBook = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input: str = input("Enter a command: ")
        if not user_input.strip():
            print(f"Please enter a command. Example: {COMMAND_TEMPLATES[Command.ADD]}")
            continue
        command, args, raw_command = parse_input(user_input)

        if command in {Command.CLOSE, Command.EXIT}:
            print("Good bye!")
            break

        if command == Command.HELLO:
            print("How can I help you?")
        elif command == Command.ADD:
            print(add_contact(args, book))
        elif command == Command.CHANGE:
            print(change_phone(args, book))
        elif command == Command.PHONE:
            print(show_phone(args, book))
        elif command == Command.ALL:
            print(show_all(args, book))
        elif command == Command.ADD_BIRTHDAY:
            print(add_birthday(args, book))
        elif command == Command.SHOW_BIRTHDAY:
            print(show_birthday(args, book))
        elif command == Command.BIRTHDAYS:
            print(birthdays(args, book))
        elif command == Command.HELP:
            print(show_commands(args, book))
        elif command is None:
            print(format_unknown_command_message(raw_command))
        else:
            print("Unexpected command handling error.")


if __name__ == "__main__":
    main()
