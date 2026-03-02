import sys
import subprocess
import os

if __name__ == "__main__":
    test_args = sys.argv[1:]
    
    # Path to the virtual env python and manage.py
    python_exec = r"F:\python\envs\.venv_web\scripts\python.exe"
    manage_py = os.path.join(os.getcwd(), "manage.py")
    
    cmd = [python_exec, manage_py, "test"] + test_args + ["--noinput"]
    
    print(f"Running tests: {' '.join(test_args)}\nOutput will be redirected to test_output.txt")
    
    # Run the tests and redirect all output to test_output.txt
    with open("test_output.txt", "w", encoding="utf-8") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    
    sys.exit(result.returncode)

