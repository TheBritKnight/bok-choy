"""
Use environment variables to configure Selenium remote WebDriver.
For use with SauceLabs (via SauceConnect) or local browsers.
"""

import os
import splinter

import logging
LOGGER = logging.getLogger(__name__)


EXPECTED_ENV_VARS = [
    'SELENIUM_BROWSER',
    'SELENIUM_VERSION',
    'SELENIUM_PLATFORM',
    'SELENIUM_HOST',
    'SELENIUM_PORT',
    'SAUCE_USER_NAME',
    'SAUCE_API_KEY',
]


OPTIONAL_ENV_VARS = [
    'JOB_NAME',
    'BUILD_NUMBER',
]


BROWSERS = ['chrome', 'firefox', 'internet explorer', 'safari']


class BrowserConfigError(Exception):
    """
    Misconfiguration error in the environment variables.
    """
    pass


def browser(tags):
    """
    Interpret environment variables to configure Selenium.
    Performs validation, logging, and sensible defaults.

    `tags` is a list of string tags to apply to the SauceLabs
    job.  If not using SauceLabs, these will be ignored.

    There are two cases:

    1. Local browsers: No environment variables set (default to Firefox locally) or `SELENIUM_BROWSER` set (use that browser locally)

    2. SauceLabs: Set all of the following environment variables:

        * SELENIUM_BROWSER
        * SELENIUM_VERSION
        * SELENIUM_PLATFORM
        * SELENIUM_HOST
        * SELENIUM_PORT
        * SAUCE_USER_NAME
        * SAUCE_API_KEY

    **NOTE:** these are the environment variables set by the SauceLabs
    Jenkins plugin.

    Optionally provide Jenkins info, used to identify jobs to Sauce:

        * JOB_NAME
        * BUILD_NUMBER

    Raises a `BrowserConfigError` if environment variables are missing.
    Returns a `splinter.Browser` object.
    """

    if _use_local_browser():
        browser_name = os.environ.get('SELENIUM_BROWSER', 'firefox')
        LOGGER.info("Using local browser: {0} [Default is firefox]".format(browser_name))
        return splinter.Browser(browser_name)

    else:

        # Interpret the environment variables, raising an exception if they're invalid
        envs = _required_envs()
        envs.update(_optional_envs())

        # Turn the environment variables into a dictionary of desired capabilities
        caps = _capabilities_dict(envs, tags)

        LOGGER.info("Using SauceLabs: {0} {1} {2}".format(
            caps['platform'], caps['browserName'], caps['version']
        ))

        # Create and return a new Browser
        # We assume that the WebDriver end-point is running locally (e.g. using SauceConnect)
        url = "http://{0}:{1}/wd/hub".format(envs['SELENIUM_HOST'], envs['SELENIUM_PORT'])
        return splinter.Browser(driver_name="remote", url=url, **caps)


def _use_local_browser():
    """
    Returns a boolean indicating whether we should use a local
    browser.  This means the user has made no attempt to set
    environment variables indicating they want to connect to SauceLabs!
    """
    return all([
        key not in os.environ
        for key in EXPECTED_ENV_VARS
        if key != 'SELENIUM_BROWSER'
    ])


def _required_envs():
    """
    Parse environment variables for required values,
    raising a `BrowserConfig` error if they are not found.

    Returns a `dict` of environment variables.
    """
    envs = {
        key: os.environ.get(key)
        for key in EXPECTED_ENV_VARS
    }

    # Check for missing keys
    missing = [key for key, val in envs.items() if val is None]
    if len(missing) > 0:
        msg = (
            "These environment variables must be set: " +
            ", ".join(missing)
        )
        raise BrowserConfigError(msg)

    # Check that we support this browser
    if envs['SELENIUM_BROWSER'] not in BROWSERS:
        msg = "Unsuppported browser: {0}".format(envs['SELENIUM_BROWSER'])
        raise BrowserConfigError(msg)

    return envs


def _optional_envs():
    """
    Parse environment variables for optional values,
    raising a `BrowserConfig` error if they are insufficiently specified.

    Returns a `dict` of environment variables.
    """
    envs = {
        key: os.environ.get(key)
        for key in OPTIONAL_ENV_VARS
        if key in os.environ
    }

    # If we're using Jenkins, check that we have all the required info
    if 'JOB_NAME' in envs and 'BUILD_NUMBER' not in envs:
        raise BrowserConfigError("Missing BUILD_NUMBER environment var")

    if 'BUILD_NUMBER' in envs and 'JOB_NAME' not in envs:
        raise BrowserConfigError("Missing JOB_NAME environment var")

    return envs


def _capabilities_dict(envs, tags):
    """
    Convert the dictionary of environment variables to
    a dictionary of desired capabilities to send to the
    Remote WebDriver.

    `tags` is a list of string tags to apply to the SauceLabs job.
    """
    capabilities = {
        'browserName': envs['SELENIUM_BROWSER'],
        'platform': envs['SELENIUM_PLATFORM'],
        'version': envs['SELENIUM_VERSION'],
        'username': envs['SAUCE_USER_NAME'],
        'accessKey': envs['SAUCE_API_KEY'],
        'video-upload-on-pass': False,
        'sauce-advisor': False,
        'capture-html': True,
        'record-screenshots': True,
        'max-duration': 600,
        'public': 'public restricted',
        'tags': tags,
    }

    # Optional: Add in Jenkins-specific environment variables
    # to link Sauce output with the Jenkins job
    if 'JOB_NAME' in envs:
        jenkins_vars = {'build': envs['BUILD_NUMBER'], 'name': envs['JOB_NAME']}
        capabilities.update(jenkins_vars)

    return capabilities
