from setuptools import setup
setup(
    use_scm_version=True,
    package_data = {
        '': ['*'],
    },
    entry_points = {
        'console_scripts': [
            'eventmanager = eventmanager:cli',
        ],
    },
)
