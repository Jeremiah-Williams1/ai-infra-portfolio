import sys
import json
from src.models import text_model

def main():
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    result = text_model.predict(text)
    print(json.dumps(result))

if __name__ == "__main__":
    main()