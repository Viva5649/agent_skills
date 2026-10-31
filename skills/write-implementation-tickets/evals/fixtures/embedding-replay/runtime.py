class Runtime:
    def __init__(self, engine):
        self.engine = engine
        self.loaded = False

    def load(self, path):
        self.engine.load(path)
        self.loaded = True

    def unload(self):
        self.loaded = False
        self.engine.unload()
