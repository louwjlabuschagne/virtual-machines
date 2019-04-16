import numpy as np
import pandas as pd

from re import sub
from paramiko import SSHClient
from time import gmtime, strftime
from paramiko.auth_handler import AuthenticationException

def clean_columns(df):
    """
    Function that cleans to columns of the DataFrame df
    """
    df.columns = [column.upper().\
                  replace('\n', '').\
                  replace('%', '_percentage_').\
                  replace(' ', '_').\
                  replace('SUM(', '').\
                  replace('[', '').\
                  replace(']', '').\
                  replace(')', '').\
				  replace('(', '').\
                  replace('-', '').\
                  replace('/','') for column in df.columns]
    return(df)

def log_print(message):
    """
    A function I just like using instead of print()
    """
    print('[%s]: %s'%(strftime("%Y-%m-%d %H:%M:%S", gmtime()), message))

class VM(object):
    """
    A handler to interact with linux VMs
    """
    def __init__(self, hostname, username, pkey='~/.ssh/id_rsa.pub'):
        """
        hostname :: string :: hostname with the domain for the VM
        pkey :: string :: location of ssh public key, defaults to ~/.ssh/id_rsa.pub
        """
        super(VM, self).__init__()
        self.hostname = hostname
        self.username = username
        self.pkey = pkey

        self.logged_in_emoj = '✅'
        self.logged_in = True
        try:
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.connect(hostname=self.hostname,
                        username=self.username,
                        key_filename=self.pkey)
            ssh.close()
        except AuthenticationException as exception:
            log_print(exception)
            log_print('AuthenticationException raised for'%(self.username+'@'+self.hostname))
            self.logged_in_emoj = '⛔️'
            self.logged_in = False

    def __str__(self):
        """
        Default print method for the VM class
        Pandas uses this to display the object in a DataFrame
        """
        return(self.username+'@'+self.hostname+' '+self.logged_in_emoj)

    def cmd_df(self):
        """
        A method that retuns the output of the bash command "df"
        """
        df_lines = self.exec_command('df')
        df = clean_columns(pd.DataFrame(columns=df_lines[0].split(maxsplit=5)))

        for line in df_lines[1:]:
            values = pd.DataFrame(line.split(maxsplit=5), index=df.columns).T
            df = pd.concat([df, values], axis=0)

        df.USE_percentage_ = df.USE_percentage_.str.strip('%').astype(float)/100
        df.reset_index(drop=True, inplace=True)
        return(df)

    def parse_key_value_output(self, cmd='lscpu'):
        """
        Method that inferres a DataFrame from
        the lines of the `cmd` bash command ran

        If the output is in the format
        MemTotal:       329756556 kB
        MemFree:        315845184 kB
        MemAvailable:   325093600 kB
        Buffers:         1690408 kB

        which is the case for most linux performance outputs, then this method will cast
        the output into a DataFrame.

        Parameters
        ==========
        cmd :: string :: bash command to executes

        Returns
        ==========
        DataFrame :: a dataframe with the keys as columns and the values as entries
        ARCHITECTURE    CPUOPMODES      BYTEORDER       CPUS    ...
        x86_64          32-bit,64-bit   LittleEndian    72      ...
        """
        cmd_lines = self.exec_command(cmd)

        #format output into a dataframe
        lines = {}
        for kv in [sub('\s', '', line) for line in cmd_lines if ':' in line]:
            split = kv.split(':')
            lines[split[0]] = split[1]
        df = clean_columns(pd.DataFrame(lines, index=[0]))

        return(df)

    def exec_command(self, cmd='ls /'):
        """
        Method that runs `cmd` on the connected VM and returns each line in a list.

        This is probably the method you'll use most and I advice
        creating wrapper methods, like self.cmd_df, for the special bash commands
        that you commonly use.

        Parameters
        ==========
        cmd :: string :: bash command to run on VM

        Returns
        =======
        list :: list with each line of the output as a entry in the list
        """
        #set up the SSH client
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(hostname=self.hostname,
                    username=self.username,
                    key_filename=self.pkey)
        #execute `lscpu` command on the VM
        stdin, stdout, stderr = ssh.exec_command(cmd)
        lines = stdout.readlines()
        ssh.close()
        return([l.strip('\n') for l in lines])
