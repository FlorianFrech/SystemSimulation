import ipywidgets as W

class StatusBar(W.HBox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status_label = W.Label("Ready")
        self.children = [self.status_label]
    
    def set(self, message: str, ok: bool = True):
        """Set the status message with optional success/error styling."""
        self.status_label.value = message
        # Add styling based on ok parameter
        if ok:
            self.status_label.style = {'text_color': 'green'}
        else:
            self.status_label.style = {'text_color': 'red'}