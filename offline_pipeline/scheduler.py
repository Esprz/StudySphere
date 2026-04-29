"""Thin root wrapper so the container can run `python scheduler.py`."""

from src.scheduler import main


if __name__ == "__main__":
    main()
