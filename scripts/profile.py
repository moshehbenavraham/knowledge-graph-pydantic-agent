#!/usr/bin/env python3
"""
Performance Profiling Script using py-spy

This script provides various profiling options for the Agentic RAG application.
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path
import time

def run_pyspy_command(args):
    """Run py-spy with the given arguments"""
    cmd = ["py-spy"] + args
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd)

def profile_api(duration=30, output="api-flamegraph.svg"):
    """Profile the FastAPI application"""
    print(f"Profiling API for {duration} seconds...")
    args = [
        "record",
        "-d", str(duration),
        "-f", "flamegraph",
        "-o", output,
        "--", 
        "python", "-m", "src.api.main"
    ]
    return run_pyspy_command(args)

def profile_streamlit(duration=30, output="ui-flamegraph.svg"):
    """Profile the Streamlit UI"""
    print(f"Profiling Streamlit UI for {duration} seconds...")
    args = [
        "record",
        "-d", str(duration),
        "-f", "flamegraph",
        "-o", output,
        "--",
        "streamlit", "run", "src/ui/streamlit_app.py"
    ]
    return run_pyspy_command(args)

def profile_rag_pipeline(duration=30, output="rag-flamegraph.svg"):
    """Profile the RAG pipeline"""
    print(f"Profiling RAG pipeline for {duration} seconds...")
    args = [
        "record",
        "-d", str(duration),
        "-f", "flamegraph",
        "-o", output,
        "--",
        "python", "-m", "src.agentic_rag.ingestion.pipeline", "ingest"
    ]
    return run_pyspy_command(args)

def profile_running_process(pid, duration=30, output="process-flamegraph.svg"):
    """Profile an already running process"""
    print(f"Profiling process {pid} for {duration} seconds...")
    args = [
        "record",
        "-d", str(duration),
        "-f", "flamegraph",
        "-o", output,
        "-p", str(pid)
    ]
    return run_pyspy_command(args)

def top_mode(pid=None):
    """Run py-spy in top mode for real-time profiling"""
    print("Starting py-spy in top mode (press Ctrl+C to stop)...")
    args = ["top"]
    if pid:
        args.extend(["-p", str(pid)])
    else:
        args.extend(["--", "python", "-m", "src.api.main"])
    return run_pyspy_command(args)

def profile_test_suite(output="tests-flamegraph.svg"):
    """Profile the test suite execution"""
    print("Profiling test suite...")
    args = [
        "record",
        "-f", "flamegraph",
        "-o", output,
        "--",
        "pytest", "tests/", "-v"
    ]
    return run_pyspy_command(args)

def profile_memory(component="api", duration=60):
    """Profile memory usage using memory_profiler"""
    print(f"Profiling memory for {component} for {duration} seconds...")
    
    components = {
        "api": "src.api.main",
        "ui": "streamlit run src/ui/streamlit_app.py",
        "rag": "src.agentic_rag.ingestion.pipeline",
    }
    
    if component not in components:
        print(f"Unknown component: {component}")
        return 1
    
    cmd = f"mprof run -T {duration} python -m {components[component]}"
    subprocess.run(cmd, shell=True)
    
    # Generate the plot
    subprocess.run("mprof plot", shell=True)
    return 0

def profile_specific_function(module, function, duration=30, output="function-flamegraph.svg"):
    """Profile a specific function"""
    print(f"Profiling {module}:{function} for {duration} seconds...")
    
    # Create a temporary Python script to run the function
    test_script = f"""
import sys
sys.path.insert(0, '.')
from {module} import {function}

# Run the function in a loop for profiling
import time
start = time.time()
while time.time() - start < {duration}:
    {function}()
    time.sleep(0.1)
"""
    
    with open("temp_profile.py", "w") as f:
        f.write(test_script)
    
    try:
        args = [
            "record",
            "-d", str(duration),
            "-f", "flamegraph",
            "-o", output,
            "--",
            "python", "temp_profile.py"
        ]
        result = run_pyspy_command(args)
    finally:
        os.remove("temp_profile.py")
    
    return result

def generate_speedscope(input_file, output_file=None):
    """Convert flamegraph to speedscope format"""
    if output_file is None:
        output_file = input_file.replace(".svg", ".speedscope.json")
    
    args = [
        "record",
        "-f", "speedscope",
        "-o", output_file,
        input_file
    ]
    return run_pyspy_command(args)

def main():
    parser = argparse.ArgumentParser(description="Performance profiling for Agentic RAG")
    
    subparsers = parser.add_subparsers(dest="command", help="Profiling commands")
    
    # API profiling
    api_parser = subparsers.add_parser("api", help="Profile the API server")
    api_parser.add_argument("-d", "--duration", type=int, default=30, help="Duration in seconds")
    api_parser.add_argument("-o", "--output", default="api-flamegraph.svg", help="Output file")
    
    # UI profiling
    ui_parser = subparsers.add_parser("ui", help="Profile the Streamlit UI")
    ui_parser.add_argument("-d", "--duration", type=int, default=30, help="Duration in seconds")
    ui_parser.add_argument("-o", "--output", default="ui-flamegraph.svg", help="Output file")
    
    # RAG pipeline profiling
    rag_parser = subparsers.add_parser("rag", help="Profile the RAG pipeline")
    rag_parser.add_argument("-d", "--duration", type=int, default=30, help="Duration in seconds")
    rag_parser.add_argument("-o", "--output", default="rag-flamegraph.svg", help="Output file")
    
    # Process profiling
    proc_parser = subparsers.add_parser("process", help="Profile a running process")
    proc_parser.add_argument("pid", type=int, help="Process ID")
    proc_parser.add_argument("-d", "--duration", type=int, default=30, help="Duration in seconds")
    proc_parser.add_argument("-o", "--output", default="process-flamegraph.svg", help="Output file")
    
    # Top mode
    top_parser = subparsers.add_parser("top", help="Run in top mode")
    top_parser.add_argument("-p", "--pid", type=int, help="Process ID (optional)")
    
    # Test profiling
    test_parser = subparsers.add_parser("tests", help="Profile test suite")
    test_parser.add_argument("-o", "--output", default="tests-flamegraph.svg", help="Output file")
    
    # Memory profiling
    mem_parser = subparsers.add_parser("memory", help="Profile memory usage")
    mem_parser.add_argument("component", choices=["api", "ui", "rag"], help="Component to profile")
    mem_parser.add_argument("-d", "--duration", type=int, default=60, help="Duration in seconds")
    
    # Function profiling
    func_parser = subparsers.add_parser("function", help="Profile specific function")
    func_parser.add_argument("module", help="Module name")
    func_parser.add_argument("function", help="Function name")
    func_parser.add_argument("-d", "--duration", type=int, default=30, help="Duration in seconds")
    func_parser.add_argument("-o", "--output", default="function-flamegraph.svg", help="Output file")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    # Check if py-spy is installed
    if subprocess.run(["which", "py-spy"], capture_output=True).returncode != 0:
        print("py-spy is not installed. Install it with: pip install py-spy")
        return 1
    
    # Run the appropriate command
    if args.command == "api":
        return profile_api(args.duration, args.output).returncode
    elif args.command == "ui":
        return profile_streamlit(args.duration, args.output).returncode
    elif args.command == "rag":
        return profile_rag_pipeline(args.duration, args.output).returncode
    elif args.command == "process":
        return profile_running_process(args.pid, args.duration, args.output).returncode
    elif args.command == "top":
        return top_mode(args.pid).returncode
    elif args.command == "tests":
        return profile_test_suite(args.output).returncode
    elif args.command == "memory":
        return profile_memory(args.component, args.duration)
    elif args.command == "function":
        return profile_specific_function(args.module, args.function, args.duration, args.output).returncode
    
    return 0

if __name__ == "__main__":
    sys.exit(main())