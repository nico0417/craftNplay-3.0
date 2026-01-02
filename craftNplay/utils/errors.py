import traceback
import time

LOG_PATH = 'bot_errors.log'

def log_exception(exc: Exception, context: str = None):
    """Append exception traceback and context to the bot_errors.log file."""
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    header = f'[{ts}] Exception'
    if context:
        header += f' Context: {context}'
    header += '\n'
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    entry = header + tb + '\n'
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        # Best-effort: ignore logging failures
        pass
