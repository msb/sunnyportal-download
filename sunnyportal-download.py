import os
import time
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, date, timedelta
from fs import open_fs
from selenium import webdriver
from fs.copy import copy_file
from fs.errors import ResourceNotFound
from contextlib import contextmanager
import logging
import logging.config
import urllib3.exceptions

logging.config.fileConfig(os.path.join(os.path.dirname(__file__), 'logging.conf'))

LOGGER = logging.getLogger(__name__)

TOOLS_ID = 'ctl00_ContentPlaceHolder1_UserControlShowDashboard1_UserControlShowEnergyAndPower1_OpenButtonsDivImg'  # noqa: E501
PREVIOUS_ID = 'ctl00_ContentPlaceHolder1_UserControlShowDashboard1_UserControlShowEnergyAndPower1_btn_prev'  # noqa: E501
NEXT_ID = 'ctl00_ContentPlaceHolder1_UserControlShowDashboard1_UserControlShowEnergyAndPower1_btn_next'  # noqa: E501
NAV_ID = 'ctl00_ContentPlaceHolder1_UserControlShowDashboard1_UserControlShowEnergyAndPower1_TrDiagramNavigation'  # noqa: E501

SELENIUM_OPTIONS = webdriver.ChromeOptions()
SELENIUM_OPTIONS.add_experimental_option('prefs', {
    # TODO you can't mount the default directory as a volume (assume selenium re-creates it) and no
    # other directories seem to work apart from /tmp. However, it seems a bit messy mounting /tmp.
    'download': {
        'prompt_for_download': False,
        'directory_upgrade': True,
        'default_directory': '/tmp',
    }
})

SUNNYPORTAL_LANDING = 'https://www.sunnyportal.com/Templates/Login.aspx'


class Portal:
    """
    An object created by `portal_context()` that provides the ability to download generation data
    for a particular date.
    """
    def __init__(self, driver, generation_date):
        self.driver = driver
        # the current date context in the portal
        self.generation_date = generation_date

    def download(self, generation_date):
        """
        Calculates the days between the current and required date then repeatedly presses
        previous/next buttons to get to the required date then presses download button.
        """
        delta = generation_date - self.generation_date
        direction = PREVIOUS_ID if delta.days < 0 else NEXT_ID

        # navigate to required generation_date
        for _ in range(abs(delta.days)):
            self.driver.find_element_by_id(direction).click()
            time.sleep(1)  # wait for completion

        # download data
        ActionChains(self.driver).move_to_element(
            self.driver.find_element_by_id(TOOLS_ID)
        ).perform()
        time.sleep(1)  # wait for completion
        self.driver.find_element_by_css_selector('input[title=Download]').click()

        # update generation date
        self.generation_date = generation_date


@contextmanager
def portal_context():
    """
    A context manager that create a selenium resource, sign's in to the portal, and yields a
    `Portal` object.
    """
    # Create the selenium driver. Note that this connection can fail, even if the orchestration has
    # checked that the port is available for connection. So we use retry logic here instead of in
    # the orchestration.
    driver = retry(lambda: webdriver.Remote(
        command_executor=os.environ["SELENIUM_COMMAND_EXECUTOR"],
        desired_capabilities=SELENIUM_OPTIONS.to_capabilities()
    ), urllib3.exceptions.HTTPError) 

    # sign in to sunnyportal
    driver.get(SUNNYPORTAL_LANDING)
    driver.find_element_by_id('txtUserName').send_keys(os.environ["SUNNYPORTAL_USERNAME"])
    driver.find_element_by_id('txtPassword').send_keys(os.environ["SUNNYPORTAL_PASSWORD"])
    driver.find_element_by_class_name('button').click()
    time.sleep(1)  # wait for completion

    yield Portal(
        driver, 
        # the portals date context always starts at today's date
        datetime.now().date()
    )  # TODO don't yet know best strategy for handling errors

    # close browser window
    driver.close()


def generation_dates():
    """Function that generates date from yesterday to the defined start date."""
    start_date = date.fromisoformat(os.environ['START_DATE'])
    generation_date = datetime.now().date() - timedelta(days=1)
    while generation_date >= start_date:
        yield generation_date
        generation_date -= timedelta(days=1)


def main():
    """
    This script retrieves solar generation data from www.sunnyportal.com. As no API is provided by
    the host it uses a remote selenium resource to drive the UI to download the data. The Chrome
    provider is used as this is more amenable to file downloads. The script assumes that the
    directory selenium downloads the data to will be accessible as, once downloaded it copy the
    file to a store.

    The script starts from yesterday and works backwards to a defined start date downloading and
    copying a day's worth of data if it isn't already in the store.

    The environment variables that the script requires are described in 
    `sunnyportal-download.env.in`.
    """

    LOGGER.info('getting store files list')
    input_path = open_fs(os.environ['FILE_STORE_PATH'])
    uploaded = {file.name for step in input_path.walk(filter=['*.csv']) for file in step.files}
    LOGGER.info(f'{len(uploaded)} found')

    downloads_path = open_fs(os.environ['DOWNLOADS_PATH'])
    downloads = {
        file.name: f'{step.path}/{file.name}'
        for step in downloads_path.walk(filter=['*.csv']) for file in step.files
        if file.name in uploaded
    }
    LOGGER.info(f'{len(downloads)} files already in downloads path')

    # create a Portal 
    with portal_context() as portal:
        # interate over the possible generation dates 
        for generation_date in generation_dates():
            file_name = f'Energy_and_Power_Day_{generation_date}.csv'
            if file_name not in uploaded:
                LOGGER.info(f'processing {file_name}')
                if file_name not in downloads:
                    portal.download(generation_date)
                    downloads[file_name] = file_name
                # copy the downloaded data to the store
                retry(
                    lambda: copy_file(downloads_path, downloads[file_name], input_path, file_name),
                    ResourceNotFound
                )


def retry(task, retry_error, tries=5, wait=1):
    """
    Tries to complete a callable `task` `tries` times, retrying if `retry_error` is raised waiting
    `wait` seconds between each try.
    """
    try:
        return task()
    except retry_error as e:
        tries -= 1
        if tries == 0:
            raise e
        else:
            LOGGER.warning(f'failed - waiting {wait} seconds to retry')
            time.sleep(wait)
            return retry(task, retry_error, tries, wait)


if __name__ == "__main__":
    main()
