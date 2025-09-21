#!/usr/bin/env python3
"""
Enhanced Terminal Command Engine with AI and History Features - Web Compatible
Fixed to work properly with Flask backend by removing blocking input() calls
"""

import os
import shutil
import psutil
import subprocess
import sys
import glob
import datetime
from pathlib import Path

# Try to import AI capabilities
try:
    import google.generativeai as genai
    # Configure Google AI with your API key
    api_key = os.getenv('GOOGLE_AI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
        ai_model = genai.GenerativeModel('gemini-1.5-flash')
        ai_available = True
    else:
        print("Warning: GOOGLE_AI_API_KEY not set. AI features disabled.")
        ai_available = False
except ImportError:
    print("Warning: google-generativeai not installed. AI features disabled.")
    ai_available = False
except Exception as e:
    print(f"Warning: AI features disabled. Error: {e}")
    ai_available = False

class TerminalEngine:
    def __init__(self):
        """Initialize the terminal engine with command history and built-in commands."""
        self.command_history = []
        self.current_directory = os.getcwd()
        self.web_mode = True  # Flag to indicate we're running in web mode
        
        # Built-in commands mapping
        self.builtin_commands = {
            'pwd': self.cmd_pwd,
            'ls': self.cmd_ls,
            'cd': self.cmd_cd,
            'mkdir': self.cmd_mkdir,
            'rm': self.cmd_rm,
            'cp': self.cmd_cp,
            'mv': self.cmd_mv,
            'cpu': self.cmd_cpu,
            'mem': self.cmd_mem,
            'ps': self.cmd_ps,
            'history': self.cmd_history,
            'clear': self.cmd_clear,
            'help': self.cmd_help,
            'whoami': self.cmd_whoami,
            'date': self.cmd_date,
            'cat': self.cmd_cat,
            'touch': self.cmd_touch,
            'find': self.cmd_find
        }

    def get_prompt(self):
        """Generate a custom prompt showing current directory."""
        username = os.getenv('USER', 'user')
        current_dir = os.path.basename(self.current_directory) or self.current_directory
        return f"{username}@terminal:{current_dir}$ "

    def cmd_pwd(self, args):
        """Print working directory."""
        print(self.current_directory)

    def cmd_ls(self, args):
        """List directory contents with optional flags."""
        show_hidden = '-a' in args
        long_format = '-l' in args
        
        try:
            items = os.listdir(self.current_directory)
            if not show_hidden:
                items = [item for item in items if not item.startswith('.')]
            
            items.sort()
            
            if long_format:
                print(f"{'Permissions':<12} {'Size':<10} {'Modified':<20} {'Name'}")
                print("-" * 60)
                for item in items:
                    item_path = os.path.join(self.current_directory, item)
                    try:
                        stat = os.stat(item_path)
                        size = stat.st_size
                        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        perms = oct(stat.st_mode)[-3:]
                        is_dir = "d" if os.path.isdir(item_path) else "-"
                        print(f"{is_dir}{perms:<11} {size:<10} {mtime:<20} {item}")
                    except OSError:
                        print(f"{'?':<12} {'?':<10} {'?':<20} {item}")
            else:
                for item in items:
                    item_path = os.path.join(self.current_directory, item)
                    if os.path.isdir(item_path):
                        print(f"{item}/")
                    else:
                        print(item)
                        
        except PermissionError:
            print("Error: Permission denied")
        except OSError as e:
            print(f"Error: {e}")

    def cmd_cd(self, args):
        """Change directory."""
        if not args:
            # Go to home directory
            target_dir = os.path.expanduser("~")
        else:
            target_dir = " ".join(args)
            
        # Handle relative paths
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.current_directory, target_dir)
            
        try:
            # Resolve the path and change directory
            resolved_path = os.path.realpath(target_dir)
            os.chdir(resolved_path)
            self.current_directory = resolved_path
            
        except FileNotFoundError:
            print("Error: No such file or directory")
        except PermissionError:
            print("Error: Permission denied")
        except OSError as e:
            print(f"Error: {e}")

    def cmd_mkdir(self, args):
        """Create directory with optional recursive flag."""
        if not args:
            print("Usage: mkdir [-p] <directory_name>")
            return
            
        recursive = '-p' in args
        if recursive:
            args.remove('-p')
            
        if not args:
            print("Usage: mkdir [-p] <directory_name>")
            return
            
        for directory_name in args:
            if not os.path.isabs(directory_name):
                directory_path = os.path.join(self.current_directory, directory_name)
            else:
                directory_path = directory_name
                
            try:
                if recursive:
                    os.makedirs(directory_path, exist_ok=True)
                else:
                    os.mkdir(directory_path)
                print(f"Directory '{directory_name}' created successfully")
                
            except FileExistsError:
                print(f"Error: Directory '{directory_name}' already exists")
            except PermissionError:
                print("Error: Permission denied")
            except OSError as e:
                print(f"Error: {e}")

    def cmd_rm(self, args):
        """Remove files or directories - SIMPLIFIED for web mode."""
        if not args:
            print("Usage: rm [-rf] <file_or_directory>")
            return
            
        recursive = '-r' in args or '-rf' in args
        force = '-f' in args or '-rf' in args
        
        # Remove flags from args
        args = [arg for arg in args if not arg.startswith('-')]
        
        if not args:
            print("Usage: rm [-rf] <file_or_directory>")
            return
            
        for item_name in args:
            if not os.path.isabs(item_name):
                item_path = os.path.join(self.current_directory, item_name)
            else:
                item_path = item_name
                
            if not os.path.exists(item_path):
                print(f"Error: '{item_name}' not found")
                continue
                
            # In web mode, always require force flag for safety
            if not force:
                print(f"Error: Use -f flag to delete '{item_name}' in web mode for safety")
                continue
                    
            try:
                if os.path.isdir(item_path):
                    if recursive:
                        shutil.rmtree(item_path)
                        print(f"Directory '{item_name}' deleted successfully")
                    else:
                        os.rmdir(item_path)
                        print(f"Directory '{item_name}' deleted successfully")
                else:
                    os.remove(item_path)
                    print(f"File '{item_name}' deleted successfully")
                    
            except OSError as e:
                print(f"Error deleting '{item_name}': {e}")

    def cmd_cp(self, args):
        """Copy files or directories."""
        if len(args) < 2:
            print("Usage: cp [-r] <source> <destination>")
            return
            
        recursive = '-r' in args
        if recursive:
            args.remove('-r')
            
        if len(args) != 2:
            print("Usage: cp [-r] <source> <destination>")
            return
            
        source, destination = args
        
        # Handle relative paths
        if not os.path.isabs(source):
            source = os.path.join(self.current_directory, source)
        if not os.path.isabs(destination):
            destination = os.path.join(self.current_directory, destination)
            
        try:
            if os.path.isdir(source):
                if recursive:
                    shutil.copytree(source, destination)
                else:
                    print("Error: Use -r flag to copy directories")
                    return
            else:
                shutil.copy2(source, destination)
            print(f"'{args[0]}' copied to '{args[1]}' successfully")
            
        except FileNotFoundError:
            print(f"Error: Source '{args[0]}' not found")
        except PermissionError:
            print("Error: Permission denied")
        except shutil.SameFileError:
            print("Error: Source and destination are the same")
        except OSError as e:
            print(f"Error: {e}")

    def cmd_mv(self, args):
        """Move/rename files or directories."""
        if len(args) != 2:
            print("Usage: mv <source> <destination>")
            return
            
        source, destination = args
        
        # Handle relative paths
        if not os.path.isabs(source):
            source = os.path.join(self.current_directory, source)
        if not os.path.isabs(destination):
            destination = os.path.join(self.current_directory, destination)
            
        try:
            shutil.move(source, destination)
            print(f"'{args[0]}' moved to '{args[1]}' successfully")
            
        except FileNotFoundError:
            print(f"Error: Source '{args[0]}' not found")
        except PermissionError:
            print("Error: Permission denied")
        except OSError as e:
            print(f"Error: {e}")

    def cmd_cpu(self, args):
        """Show CPU usage and information."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            print(f"CPU Usage: {cpu_usage}%")
            print(f"CPU Cores: {cpu_count}")
            if cpu_freq:
                print(f"CPU Frequency: {cpu_freq.current:.2f} MHz")
                
        except Exception as e:
            print(f"Error: Unable to get CPU information - {e}")

    def cmd_mem(self, args):
        """Show memory usage information."""
        try:
            memory_info = psutil.virtual_memory()
            swap_info = psutil.swap_memory()
            
            total_gb = memory_info.total / (1024**3)
            available_gb = memory_info.available / (1024**3)
            used_gb = memory_info.used / (1024**3)
            used_percent = memory_info.percent
            
            print(f"Memory Usage:")
            print(f"  Total: {total_gb:.1f}GB")
            print(f"  Used: {used_gb:.1f}GB ({used_percent}%)")
            print(f"  Available: {available_gb:.1f}GB")
            
            if swap_info.total > 0:
                swap_total_gb = swap_info.total / (1024**3)
                swap_used_gb = swap_info.used / (1024**3)
                print(f"Swap: {swap_used_gb:.1f}GB / {swap_total_gb:.1f}GB ({swap_info.percent}%)")
                
        except Exception as e:
            print(f"Error: Unable to get memory information - {e}")

    def cmd_ps(self, args):
        """Show running processes."""
        try:
            limit = 20
            if args and args[0].isdigit():
                limit = int(args[0])
                
            process_count = 0
            print(f"{'PID':<8} {'CPU%':<6} {'MEM%':<6} {'NAME':<30}")
            print("-" * 50)
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if process_count >= limit:
                    break
                    
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    cpu_percent = proc.info['cpu_percent'] or 0
                    mem_percent = proc.info['memory_percent'] or 0
                    
                    print(f"{pid:<8} {cpu_percent:<6.1f} {mem_percent:<6.1f} {name[:30]:<30}")
                    process_count += 1
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            print(f"\nShowing {process_count} processes (use 'ps <number>' to show more)")
            
        except Exception as e:
            print(f"Error: Unable to get process information - {e}")

    def cmd_history(self, args):
        """Show command history with optional search."""
        if not self.command_history:
            print("No command history available.")
            return
            
        search_term = " ".join(args) if args else None
        
        matching_commands = []
        for i, cmd in enumerate(self.command_history, 1):
            if search_term is None or search_term.lower() in cmd.lower():
                matching_commands.append((i, cmd))
                
        if not matching_commands:
            print(f"No commands found matching '{search_term}'")
            return
            
        for i, cmd in matching_commands[-50:]:  # Show last 50 matching commands
            print(f"{i:4}: {cmd}")

    def cmd_clear(self, args):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def cmd_help(self, args):
        """Show help information."""
        print("Available built-in commands:")
        print("  pwd              - Print working directory")
        print("  ls [-a] [-l]     - List directory contents")
        print("  cd [directory]   - Change directory")
        print("  mkdir [-p] <dir> - Create directory")
        print("  rm [-rf] <file>  - Remove file or directory (requires -f in web mode)")
        print("  cp [-r] <s> <d>  - Copy file or directory")
        print("  mv <source> <d>  - Move/rename file or directory")
        print("  cat <file>       - Display file contents")
        print("  touch <file>     - Create empty file")
        print("  find <pattern>   - Find files matching pattern")
        print("  cpu              - Show CPU information")
        print("  mem              - Show memory information")
        print("  ps [count]       - Show running processes")
        print("  history [search] - Show command history")
        print("  whoami           - Show current user")
        print("  date             - Show current date and time")
        print("  clear            - Clear screen")
        print("  help             - Show this help")
        print("  exit             - Exit terminal")
        print("\nNatural Language: Try commands like 'show me all python files' or 'create a new directory called test'")

    def cmd_whoami(self, args):
        """Show current user."""
        print(os.getenv('USER', 'unknown'))

    def cmd_date(self, args):
        """Show current date and time."""
        print(datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y'))

    def cmd_cat(self, args):
        """Display file contents."""
        if not args:
            print("Usage: cat <filename>")
            return
            
        for filename in args:
            if not os.path.isabs(filename):
                filepath = os.path.join(self.current_directory, filename)
            else:
                filepath = filename
                
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    print(content)
            except FileNotFoundError:
                print(f"Error: File '{filename}' not found")
            except PermissionError:
                print(f"Error: Permission denied accessing '{filename}'")
            except Exception as e:
                print(f"Error reading '{filename}': {e}")

    def cmd_touch(self, args):
        """Create empty file or update timestamp."""
        if not args:
            print("Usage: touch <filename>")
            return
            
        for filename in args:
            if not os.path.isabs(filename):
                filepath = os.path.join(self.current_directory, filename)
            else:
                filepath = filename
                
            try:
                Path(filepath).touch()
                print(f"File '{filename}' created/updated successfully")
            except PermissionError:
                print(f"Error: Permission denied creating '{filename}'")
            except Exception as e:
                print(f"Error creating '{filename}': {e}")

    def cmd_find(self, args):
        """Find files matching a pattern."""
        if not args:
            print("Usage: find <pattern>")
            return
            
        pattern = args[0]
        
        try:
            matches = glob.glob(os.path.join(self.current_directory, "**", pattern), recursive=True)
            
            if matches:
                print(f"Found {len(matches)} matches:")
                for match in sorted(matches):
                    rel_path = os.path.relpath(match, self.current_directory)
                    print(f"  {rel_path}")
            else:
                print(f"No files found matching '{pattern}'")
                
        except Exception as e:
            print(f"Error searching for '{pattern}': {e}")

    def translate_natural_language(self, user_input):
        """Translate natural language input to shell command using AI."""
        if not ai_available:
            return None
            
        try:
            prompt = (
                "Translate the following natural language request into a single, executable shell command "
                "for a Linux/Unix environment. Provide only the raw command and nothing else. "
                "If multiple commands are needed, separate them with &&.\n\n"
                f"Request: {user_input}"
            )
            
            response = ai_model.generate_content(prompt)
            
            if response and response.text:
                command = response.text.strip()
                # Clean up any code block markers
                if command.startswith('```'):
                    lines = command.split('\n')
                    command = lines[1] if len(lines) > 1 else command
                if command.endswith('```'):
                    command = command[:-3].strip()
                    
                return command
                
        except Exception as e:
            print(f"AI translation error: {e}")
            
        return None

    def is_likely_natural_language(self, user_input):
        """Check if input looks like natural language rather than a command."""
        command_parts = user_input.split()
        if len(command_parts) < 3:
            return False
            
        # Check for natural language indicators
        nl_indicators = ['show', 'list', 'find', 'create', 'delete', 'copy', 'move', 'what', 'how', 'where', 'all', 'me', 'the']
        return any(word.lower() in nl_indicators for word in command_parts[:3])

    def execute_command(self, user_input):
        """Execute a command (built-in or external)."""
        if not user_input.strip():
            return
            
        # Store in history
        self.command_history.append(user_input)
        
        # Handle command chaining with &&
        if '&&' in user_input:
            commands = [cmd.strip() for cmd in user_input.split('&&')]
            for cmd in commands:
                if not self.execute_single_command(cmd):
                    break  # Stop on first failure
        else:
            self.execute_single_command(user_input)

    def execute_single_command(self, user_input):
        """Execute a single command and return success status."""
        command_parts = user_input.split()
        command = command_parts[0]
        args = command_parts[1:]
        
        # Check for built-in commands first
        if command in self.builtin_commands:
            try:
                self.builtin_commands[command](args)
                return True
            except Exception as e:
                print(f"Error executing {command}: {e}")
                return False
        
        # Try AI translation for natural language - NO CONFIRMATION IN WEB MODE
        elif ai_available and self.is_likely_natural_language(user_input):
            ai_command = self.translate_natural_language(user_input)
            
            if ai_command:
                print(f"AI translated: '{user_input}' → '{ai_command}'")
                print("Executing translated command...")
                return self.execute_external_command(ai_command.split())
            else:
                print("Could not translate natural language to command")
                return False
        
        # Try as external command
        return self.execute_external_command(command_parts)

    def execute_external_command(self, command_parts):
        """Execute external system command."""
        try:
            result = subprocess.run(
                command_parts,
                cwd=self.current_directory,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.stdout:
                print(result.stdout.strip())
            
            if result.stderr:
                print(result.stderr.strip())
            
            if not result.stdout and not result.stderr and result.returncode != 0:
                print(f"Command exited with return code: {result.returncode}")
                
            return result.returncode == 0
            
        except FileNotFoundError:
            print("Error: Command not found")
            return False
        except PermissionError:
            print("Error: Permission denied")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def run(self):
        """Main terminal loop - only used when running standalone."""
        print("Enhanced Terminal Command Engine")
        print("Type 'help' for available commands or 'exit' to quit.")
        print("AI-powered natural language commands are available!\n")
        
        self.web_mode = False  # Disable web mode for standalone usage
        
        while True:
            try:
                user_input = input(self.get_prompt()).strip()
                
                if user_input == "exit":
                    print("Goodbye!")
                    break
                elif user_input:
                    self.execute_command(user_input)
                    
            except KeyboardInterrupt:
                print("\n")
                break
            except EOFError:
                print("\nGoodbye!")
                break

def main():
    """Entry point of the script."""
    terminal = TerminalEngine()
    terminal.run()

if __name__ == "__main__":
    main()
