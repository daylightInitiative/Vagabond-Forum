import subprocess
import platform
import os

def validate_dict_members(data: dict, arguments: list) -> None:
    if not isinstance(data, dict):
        raise TypeError("Argument must be a dictionary")
    
    required_keys = set(arguments)
    
    if not required_keys.issubset(data.keys()):
        missing = required_keys - data.keys()
        raise KeyError(f"Missing required keys: {missing}")

# provides the setup scripts with a cross platform implementation for running inital psql commands
def run_psql_cmd(pgopts: dict, commands: list) -> int:
    current_os = platform.system()

    try:
        validate_dict_members(pgopts, ["user", "database", "host", "password"])

        # construct database uri
        db_user = pgopts["user"]
        db_password = pgopts["password"]
        db_database = pgopts["database"]
        db_host = pgopts["host"]
        connection_uri = f"postgresql://{db_user}:{db_password}@{db_host}/{db_database}"

        login_psql = None
        if current_os == "Windows":
            # go into wsl, open psql shell and setup users
    
            login_psql = [
                "wsl",
                "psql", 
                connection_uri
            ]
    
        elif current_os == "Linux":
    
            login_psql = [
                "psql", 
                connection_uri
            ]
            
        else:
            print("Currently unsupported platform.")
            return

        process = subprocess.Popen(
            login_psql,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # add the newline and semicolon
        formatted_commands = []
        for cmd in commands:
            fmt_cmd = f"{cmd.strip('\n')}\n"
            if fmt_cmd[-1] != ';': fmt_cmd += ';' # ensure theres a semicolon at the end
            formatted_commands.append(fmt_cmd)
        formatted_commands.append("\\q\n")

        sql_command = ''.join(formatted_commands)
        print(sql_command)
        stdout_data, stderr_data = process.communicate(input=sql_command)
        
        if process.returncode == 0:
            users = [line.strip() for line in stdout_data.splitlines() if line.strip()]
            print("PostgreSQL Users:", users)
        else:
            print(f"Error ({process.returncode}):", stderr_data)
    except Exception as e:
        print("An unexpected error occured while running psql query. Error: ", e)
    finally:
        print("Cleaning up...")
        if 'process' in locals() and process.poll() is None:
            process.kill()
        print("Shell closed.")