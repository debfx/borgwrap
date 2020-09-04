# borgwrap

borgwrap is yet another thin wrapper around [borgbackup](https://github.com/borgbackup/borg).

It depends only on Python 3 and PyYAML.


# Usage

```
borgwrap [-h] --config CONFIG [--dry-run] {create,list,prune,nagios-check-age,cmd} ...

borgbackup wrapper

positional arguments:
  {create,list,prune,nagios-check-age,cmd}
    create              Create a backup archive
    list                List backup archives
    prune               Prune archives according to the config settings
    nagios-check-age    Check last backup age, usable as a Icinga/Nagios check
    cmd                 Run a borgbackup command. Exports the remote archive as BORG_REPO so it can be referenced as "::".

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Path to the config file
  --dry-run, -n         Perform a trial run with no changes made
```

See also the [example config](borgbackup.yml)


# Examples

Create a backup and prune archives according to the config settings:

```
borgwrap -c borgbackup.yaml create --stats
```

Mount the backup archives:

```
borgwrap -c borgbackup.yaml cmd -- mount :: /mnt
```
