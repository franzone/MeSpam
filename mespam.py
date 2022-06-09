import sys

def main() -> int:
    if len(sys.argv) >= 2:
        name = sys.argv[1]
    else:
        name = 'World'

    print('Hello', name)
    return 0

if __name__ == '__main__':
    sys.exit(main())
