import wx
from websocket import frame_buffer

from engine import VideoFeed

ID_OPEN = 10000
ID_SAVEAS = 10001
ID_UNDO = 10002
ID_REDO = 10003
ID_NEWEFFECT = 10004
ID_PLAY = 11000
ID_REPEAT = 11001
ID_SLIDER = 11002


#####################################################################
# wx.Frame MainFrame
#####################################################################
class MainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        self.playing = False
        self.repeat = False
        self.changed = False
        self.feed: VideoFeed = None

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((576, 432))

        # <toolbar>
        self.toolbar = wx.ToolBar(self, -1, style=wx.TB_DEFAULT_STYLE | wx.TB_TEXT | wx.TB_HORZ_TEXT)
        self.SetToolBar(self.toolbar)
        self.toolbar.AddTool(ID_OPEN, r"Открыть",
                             wx.Bitmap("icons\\open.png", wx.BITMAP_TYPE_ANY),
                             wx.Bitmap("icons\\open.disabled.png", wx.BITMAP_TYPE_ANY),
                             wx.ITEM_NORMAL, r"Открыть видео...", "")
        self.toolbar.AddTool(ID_SAVEAS, r"Сохранить как",
                             wx.Bitmap("icons\\save.png", wx.BITMAP_TYPE_ANY),
                             wx.Bitmap("icons\\save.disabled.png", wx.BITMAP_TYPE_ANY),
                             wx.ITEM_NORMAL, r"Сохранить видео как...", "")
        self.toolbar.AddSeparator()
        self.toolbar.AddTool(ID_UNDO, r"Отменить",
                             wx.Bitmap("icons\\undo.png", wx.BITMAP_TYPE_ANY),
                             wx.Bitmap("icons\\undo.disabled.png", wx.BITMAP_TYPE_ANY),
                             wx.ITEM_NORMAL, r"Отменить", "")
        self.toolbar.AddTool(ID_REDO, r"Повторить",
                             wx.Bitmap("icons\\redo.png", wx.BITMAP_TYPE_ANY),
                             wx.Bitmap("icons\\redo.disabled.png", wx.BITMAP_TYPE_ANY),
                             wx.ITEM_NORMAL, r"Повторить", "")
        self.toolbar.AddSeparator()
        self.toolbar.AddTool(ID_NEWEFFECT, r"Новый эффект",
                             wx.Bitmap("icons\\effect.png", wx.BITMAP_TYPE_ANY),
                             wx.Bitmap("icons\\effect.disabled.png", wx.BITMAP_TYPE_ANY),
                             wx.ITEM_NORMAL, r"Новый эффект", "")
        # </toolbar>

        self.video_frame = wx.Panel(self, wx.ID_ANY)

        # <panel>
        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_STATIC)
        self.play_button = wx.BitmapButton(self.panel, ID_PLAY,
                                           wx.Bitmap("icons\\play.png", wx.BITMAP_TYPE_ANY))
        self.play_button.SetBitmapDisabled(wx.Bitmap("icons\\play.disabled.png", wx.BITMAP_TYPE_ANY))
        self.repeat_button = wx.BitmapButton(self.panel, ID_REPEAT,
                                             wx.Bitmap("icons\\repeat.png", wx.BITMAP_TYPE_ANY))
        self.slider = wx.Slider(self.panel, ID_SLIDER, 0, 0, 10)
        # </panel>

        self.__set_properties()
        self.__do_layout()
        self.__update_ui()
        self.SetBackgroundColour('White')

        # Set events
        self.Bind(wx.EVT_TOOL, self.onToolbarClick, id=wx.ID_ANY)
        self.Bind(wx.EVT_BUTTON, self.onButtonClick, id=wx.ID_ANY)
        self.Bind(wx.EVT_CLOSE, self.onClose, id=wx.ID_ANY)

        # Set timer, slider and custom paint bindings
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onUpdate, self.timer)
        self.Bind(wx.EVT_SCROLL, self.onScrool, id=ID_SLIDER)
        self.video_frame.Bind(wx.EVT_ERASE_BACKGROUND, self.onEraseBackground)
        self.video_frame.Bind(wx.EVT_PAINT, self.onPaint)

    def __set_properties(self):
        self.SetTitle(r"PyVideo")
        self.toolbar.Realize()
        self.play_button.SetSize(self.play_button.GetBestSize())
        self.repeat_button.SetSize(self.repeat_button.GetBestSize())
        self.panel.SetMinSize((-1, 32))

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(wx.StaticLine(self, wx.ID_ANY, style=wx.LI_VERTICAL), 0, 0, 0)
        sizer_1.Add(self.video_frame, 1, wx.EXPAND, 0)
        sizer_2.Add(self.play_button, 0, 0, 0)
        sizer_2.Add(self.repeat_button, 0, 0, 0)
        sizer_2.Add(self.slider, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer_2)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def __update_ui(self):
        feed_on = self.feed is not None
        changed = self.changed
        self.toolbar.EnableTool(ID_SAVEAS, changed)
        self.toolbar.EnableTool(ID_UNDO, changed)
        self.toolbar.EnableTool(ID_REDO, False)
        self.toolbar.EnableTool(ID_NEWEFFECT, feed_on)

        play_bmp = {False: "icons\\play.png", True: "icons\\pause.png"}
        self.play_button.Enable(feed_on)
        self.play_button.SetBitmap(wx.Bitmap(play_bmp[self.playing], wx.BITMAP_TYPE_ANY))
        self.slider.Enable(feed_on)

        repeat_bmp = {False: "icons\\repeat.false.png", True: "icons\\repeat.png"}
        self.repeat_button.SetBitmap(wx.Bitmap(repeat_bmp[self.repeat], wx.BITMAP_TYPE_ANY))
        # TODO: уточнить как должна правильно отображаться кнопка повтора

    def Toggle_Play(self):
        self.playing = not self.playing
        if self.playing:
            self.timer.Start(self.feed.get_fps())
        else:
            self.timer.Stop()
        self.__update_ui()

    def onClose(self, event):
        self.timer.Stop()
        self.Destroy()

    def onScrool(self, event):
        pl = self.playing
        if pl:
            self.Toggle_Play()
        self.feed.set_position(self.slider.Value)
        if pl:
            self.Toggle_Play()

    def onUpdate(self, event):
        self.Refresh()
        pass

    def onEraseBackground(self, event):
        return

    def onPaint(self, event):
        if self.feed and self.playing:
            fw, fh = self.video_frame.GetSize()

            frame = self.feed.next_frame(fw, fh)
            if frame is None:
                if self.repeat:
                    self.feed.set_position(0)
                    frame = self.feed.next_frame(fw, fh)
                else:
                    self.Toggle_Play()
                    return
            h, w = frame.shape[:2]
            try:
                image = wx.BitmapFromBuffer(w, h, frame)
            except Exception:
                image = wx.Bitmap.FromBuffer(w, h, frame)

            dc = wx.BufferedPaintDC(self.video_frame)
            dc.DrawBitmap(image, 0, 0)
            self.slider.Value = self.feed.get_position()
        else:
            self.SetBackgroundColour('White')  # TODO: разобраться с этим костылём

    def onToolbarClick(self, event):
        file_filters = "AVI (*.avi)|*.avi|All files (*.*)|*.*"

        if event.Id == ID_OPEN:
            dialog = wx.FileDialog(None, message="Select video file...", defaultDir="",
                                   wildcard=file_filters, style=wx.FD_OPEN)
            if dialog.ShowModal() == wx.ID_OK:
                self.load_file(dialog.GetPath())
        if event.Id == ID_SAVEAS:
            dialog = wx.FileDialog(None, message="Save as...", defaultDir="",
                                   wildcard=file_filters, style=wx.FD_SAVE)
            if dialog.ShowModal() == wx.ID_OK:
                pass
        if event.Id == ID_UNDO:
            pass
        if event.Id == ID_REDO:
            pass
        if event.Id == ID_NEWEFFECT:
            pass
        event.Skip()

    def onButtonClick(self, event):
        if event.Id == ID_PLAY:
            self.Toggle_Play()
        if event.Id == ID_REPEAT:
            self.repeat = not self.repeat
        self.__update_ui()
        event.Skip()

    def load_file(self, name):
        feed = VideoFeed(name, True)
        if feed.opened():
            self.feed = feed
            self.slider.SetMax(feed.length())
            self.__update_ui()
        else:
            del feed


#####################################################################
# wx.App MainApp
#####################################################################
class MainApp(wx.App):
    def OnInit(self):
        self.frame = MainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True


#####################################################################
# main
#####################################################################
if __name__ == "__main__":
    app = MainApp(0)
    app.MainLoop()
