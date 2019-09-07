from setuptools import setup, find_packages
setup(
    name = 'eventmanager',
    version = '1.0',
    packages = find_packages(exclude=["tests"]),
    package_data = {
        '': ['*'],
    },
    install_requires = [
        'click',
        'python-dateutil',
        'inotify_simple',
        'psutil',
        'pyyaml',
        'sortedcontainers',
    ],
    entry_points = {
        'console_scripts': [
            'eventmanager = eventmanager:cli',
        ],
    },
    extras_require = {
        'test':  [
            'pylint',
            'pytest',
        ],
    },
)
