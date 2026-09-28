import sys

from diffgenome import mvp

if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "mvp":
        argv = argv[1:]
    sys.exit(mvp.main(argv))
