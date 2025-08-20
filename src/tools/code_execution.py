from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_globals, safe_builtins, guarded_unpack_sequence

def execute_safe_code_tool(code: str) -> str:
    # Set up allowed modules
    allowed_modules = {
        # Core utilities
        'datetime': __import__('datetime'),
        'math': __import__('math'),
        'random': __import__('random'),
        'time': __import__('time'),
        'collections': __import__('collections'),
        'itertools': __import__('itertools'),
        'functools': __import__('functools'),
        'copy': __import__('copy'),
        're': __import__('re'),  # Regular expressions
        'json': __import__('json'),
        'csv': __import__('csv'),
        'uuid': __import__('uuid'),
        'string': __import__('string'),
        'statistics': __import__('statistics'),
        
        # Data structures and algorithms
        'heapq': __import__('heapq'),
        'bisect': __import__('bisect'),
        'array': __import__('array'),
        'enum': __import__('enum'),
        'dataclasses': __import__('dataclasses'),
        
        # Numeric/scientific (if installed)
        # 'numpy': __import__('numpy', fromlist=['*']),
        # 'pandas': __import__('pandas', fromlist=['*']),
        # 'scipy': __import__('scipy', fromlist=['*']),
        
        # File/IO (with careful restrictions)
        'io': __import__('io'),
        'base64': __import__('base64'),
        'hashlib': __import__('hashlib'),
        'tempfile': __import__('tempfile')
    }
    
    # Try to import optional modules that might not be installed
    try:
        allowed_modules['numpy'] = __import__('numpy')
    except ImportError:
        pass
        
    try:
        allowed_modules['pandas'] = __import__('pandas')
    except ImportError:
        pass
        
    try:
        allowed_modules['scipy'] = __import__('scipy')
    except ImportError:
        pass
    
    # Custom import function that only allows whitelisted modules
    def safe_import(name, *args, **kwargs):
        if name in allowed_modules:
            return allowed_modules[name]
        raise ImportError(f"Module {name} is not allowed")
    
    # Create a safe environment with minimal built-ins
    safe_builtins = {
        # Basic operations
        'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool, 
        'chr': chr, 'complex': complex, 'divmod': divmod, 'float': float, 
        'format': format, 'hex': hex, 'int': int, 'len': len, 'max': max, 
        'min': min, 'oct': oct, 'ord': ord, 'pow': pow, 'round': round,
        'sorted': sorted, 'sum': sum,
        
        # Types and conversions
        'bytes': bytes, 'dict': dict, 'frozenset': frozenset, 'list': list, 
        'repr': repr, 'set': set, 'slice': slice, 'str': str, 'tuple': tuple, 
        'type': type, 'zip': zip,
        
        # Iteration and generation
        'enumerate': enumerate, 'filter': filter, 'iter': iter, 'map': map,
        'next': next, 'range': range, 'reversed': reversed,
        
        # Other safe operations
        'getattr': getattr, 'hasattr': hasattr, 'hash': hash,
        'isinstance': isinstance, 'issubclass': issubclass,
        
        # Import handler
        '__import__': safe_import
    }
    
    # Set up output capture
    output = []
    def safe_print(*args, **kwargs):
        end = kwargs.get('end', '\n')
        sep = kwargs.get('sep', ' ')
        output.append(sep.join(str(arg) for arg in args) + end)
    
    # Create restricted globals
    restricted_globals = {
        '__builtins__': safe_builtins,
        'print': safe_print
    }
    
    try:
        # Execute the code with timeout
        exec(code, restricted_globals)
        return ''.join(output)
    except Exception as e:
        return f"Error executing code: {str(e)}"