"""Private child process of the WinUI application; never starts a Qt UI."""
from clearscore.worker import main

if __name__ == "__main__":
    main()
