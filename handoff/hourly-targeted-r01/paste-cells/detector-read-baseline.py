        try:
            baseline = readControlJson(files, "metadata-success.json")
        except (json.JSONDecodeError, UnicodeDecodeError):
            baseline = None
