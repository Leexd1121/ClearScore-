if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        from clearscore.smoke import main
        main()
    else:
        from clearscore.app import main
        main()
