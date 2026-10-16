import logging

from app.ui.login import run_login_window


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    run_login_window()


if __name__ == "__main__":
    main()
