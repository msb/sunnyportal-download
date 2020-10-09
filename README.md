This is a containerised script that retrieves solar generation data from www.sunnyportal.com. As no
API is provided by the host it uses a remote selenium resource to drive the UI to download the 
data. The Chrome provider is used as this is more amenable to file downloads. The script assumes
that the directory selenium downloads the data to will be accessible as, once downloaded it copy
the file to a store.

The script starts from yesterday and works backwards to a defined start date downloading and
copying a day's worth of data if it isn't already in the store.

The environment variables that the script requires are described in 
[sunnyportal-download.env.in](https://raw.githubusercontent.com/msb/sunnyportal-download/master/sunnyportal-download.env.in).

A Docker Compose orchestration file has been defined to run a selenium server along at the same
time as the script. To run the script using the Compose file:

- run `mkdir sunnyportal-download; cd sunnyportal-download`
- download [the Docker Compose orchestration file](https://raw.githubusercontent.com/msb/sunnyportal-download/master/docker-compose.yml)
- download  [sunnyportal-download.env.in](https://raw.githubusercontent.com/msb/sunnyportal-download/master/sunnyportal-download.env.in), 
  rename to `sunnyportal-download.env`, and complete.
- configure a GDrive generation data file store (see below)
- run `docker-compose run sunnyportal-download` (once you have completed the following configuration)

Once the script is complete, the composed containers can be removed with `docker-compose down`

The script uses [PyFilesystem](https://github.com/pyfilesystem/pyfilesystem2) to write data files
to the store so the script can be configured to write to any file system supported by PyFilesystem
which could be useful if you aren't running docker locally. The container has been configured with
the `fs.dropboxfs`,  `fs.onedrivefs`, and `fs.googledrivefs`.

The orchestration file is configured for GDrive and the instructions are as follows:

### Configuring a GDrive generation data file store

There are different ways of authenticating to GDrive API but this example uses a GCP service
account with permission on the target directory. The set up steps are as follows:

 - Create [a GCP project](https://cloud.google.com/storage/docs/projects) to contain your cluster.
   [A Terraform module](https://github.com/msb/tf-gcp-project) has been provided to automate this 
   for you. Following the module's README you will see that this step has already been partially
   completed by the inclusion of 
   [the `project` folder](https://github.com/msb/sunnyportal-download/tree/master/project).
   Note that when running `terraform.output.sh` you should target the output at 
   [the `runner` folder](https://github.com/msb/sunnyportal-download/tree/master/runner) as the
   orchestration file expects to find the service account credentials there.
 - Allow the service account read/write permission on the target directory
   (use the email address found in the credentials file in the `runner` folder)

Then update the `sunnyportal-download.env` file with the following variables:

```
FILE_STORE_PATH=googledrive:///?root_id={the id of the target GDrive folder}
```

### Development

If you wish to make changes to the script then the source for the script and container
configuration can be cloned from [github](https://github.com/msb/sunnyportal-download). Once cloned the
container can be built and run for testing locally as follows:

```bash
docker-compose build sunnyportal-development
docker-compose run sunnyportal-development
```

The seleium/chrome downloads are shared with the script via a permanent docker volume. The contents
of the docker downloads volume can be examined using

```bash
docker run --rm -it -v sunnyportal-download_downloads:/data --entrypoint "sh" python:3.8-alpine
```
