from plex_music_browser.app import APP


def main() -> None:
    APP.run(host="127.0.0.1", port=8080, debug=True)


if __name__ == "__main__":
    main()
