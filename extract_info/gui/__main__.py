"""Entry point para la GUI: python -m extract_info.gui"""

from extract_info.gui.app import App


def main():
    """Ejecuta la aplicación GUI."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
