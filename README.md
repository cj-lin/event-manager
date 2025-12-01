# EventManager

EventManager is a lightweight workflow tool with shell utilities.
Requires Python 3.10+.
One can simply execute ``poetry install`` to install the tool.
(Strongly recommend to install in a virtual environment)

The entrypoint of EventManager is ``event-manager``.
To run EventManager, type ``event-manager start``.

# config

Config is in ``yaml`` format, execute ``event-manager config`` to see and modify it.

The structure of config file is a list of dictionaries, each dictionary can include:

* Event: Watch file path pattern, support regular expression grouping.
* Process: Shell execution after ``Event`` is detected.
* Timeout: Timeout before ``Process`` terminated.
* Success: Shell execution after ``Process`` succeeded.
* Fail: Shell execution after ``Process`` failed.
* Backup: File path pattern to backup ``Event``.

In which ``Event`` and ``Process`` are needed, others are optional.

# test

We use ``pytest`` to run our tests, all you have to do is run ``pytest`` in ``tests`` directory.

``environment.yml`` includes every modules needed to run tests.
