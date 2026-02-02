if __name__ == '__main__':
    from blescanner.__main__ import BLEScannerApp
    import asyncio

    try:
        app = BLEScannerApp()
        asyncio.run(app.app_func())
    except asyncio.CancelledError:
        pass  # Ignore TaskCancelledError when the app is closed
    except KeyboardInterrupt:
        pass
