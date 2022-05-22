from kivy.app import App
from kivy.core.window import Window


from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage, CoreImage
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.colorpicker import ColorPicker

from kivy.clock import Clock
from kivy.graphics.texture import Texture

import numpy as np 
from PIL import Image
from io import BytesIO
from perlin import PerlinNoiseFactory
from functools import partial
from threading import Thread


W, H = 1024, 512
NOISE_SCALE = 5
NOISE_OFFSET = 10
OCTAVES = 2 

def remap(value, oldMin, oldMax, newMin, newMax):
    return ((value - oldMin) * (newMax - newMin)) / (oldMax - oldMin) + newMin



class RenderThread(Thread):
    def __init__(self, app):
        Thread.__init__(self)  
        self.app = app     
        self.noise = PerlinNoiseFactory(2, octaves=OCTAVES, unbias=True) 
        self.rawData = np.zeros((H, W), dtype=np.uint8)

    def run(self):
        data = np.zeros((H, W, 3), dtype=np.uint8)
        data[0:H, 0:W] = [255, 255, 255]
        
        for x in range(H):
            for y in range(W):
                value = remap(self.noise(NOISE_OFFSET + x / W * NOISE_SCALE, NOISE_OFFSET + y / H * NOISE_SCALE), -1, 1, 0, 255)
                self.rawData[x, y] = value
                set = False
                for i, r in enumerate(self.app.ranges):
                    if value <= r:
                        data[x, y] = self.app.colors[i]
                        set = True
                        break
                if not set:
                    data[x, y] = self.app.colors[-1]

        self.app._draw(data)

    def update(self, value):
        if self.app.updating:
            return
        self.app.updating = True
        data = np.zeros((H, W, 3), dtype=np.uint8)
        
        for x in range(H):
            for y in range(W):
                set = False
                for i, r in enumerate(self.app.ranges):
                    if self.rawData[x, y] <= r:
                        data[x, y] = self.app.colors[i]
                        set = True
                        break
                if not set:
                    data[x, y] = self.app.colors[-1]

        self.app._draw(data)






class MyApp(App):
    def build(self):
        self.updating = False
        self.pickingColor = False
        self.ranges = np.linspace(0, 255, 5)[1:4]
        self.colors = [
            [255, 0, 0], 
            [0, 255, 0], 
            [0, 0, 255],
            [0, 255, 255]
        ]

        self.layout = FloatLayout(size=(W, H * 1.25))

        self.range1 = Slider(min=0, max=255, value=int(self.ranges[0]), pos=(-20, 30), size_hint=(0.5, .05), ids={"idx": "0"})
        self.range2 = Slider(min=0, max=255, value=int(self.ranges[1]), pos=(-20, 70), size_hint=(0.5, .05), ids={"idx": "1"})
        self.range3 = Slider(min=0, max=255, value=int(self.ranges[2]), pos=(-20, 110), size_hint=(0.5, .05), ids={"idx": "2"})

        self.range1.bind(value=self.updateRange)
        self.range2.bind(value=self.updateRange)
        self.range3.bind(value=self.updateRange)

        self.display = KivyImage(size_hint=(1, 0.75), pos_hint={ 'y': 0.25 })
        #self._generate(5)
        self.renderThread.start()

        self.layout.add_widget(self.display)
        self.layout.add_widget(self.range1)
        self.layout.add_widget(self.range2)
        self.layout.add_widget(self.range3)  

        self.layout.add_widget(Label(text='Range 1', pos=(W / 2 + 20, 30), size_hint=(0, .05)))      
        self.layout.add_widget(Label(text='Range 2', pos=(W / 2 + 20, 70), size_hint=(0, .05)))      
        self.layout.add_widget(Label(text='Range 3', pos=(W / 2 + 20, 110), size_hint=(0, .05)))

        self.layout.add_widget(Button(text='Pick Color 1', pos=(W / 2 + 80, 10), size_hint=(.1, .05), on_press=self.togglePicker, background_color=self.colors[0], background_normal=''))   
        self.layout.add_widget(Button(text='Pick Color 2', pos=(W / 2 + 80, 50), size_hint=(.1, .05), on_press=self.togglePicker, background_color=self.colors[1], background_normal=''))
        self.layout.add_widget(Button(text='Pick Color 3', pos=(W / 2 + 80, 90), size_hint=(.1, .05), on_press=self.togglePicker, background_color=self.colors[2], background_normal=''))
        self.layout.add_widget(Button(text='Pick Color 4', pos=(W / 2 + 80, 130), size_hint=(.1, .05), on_press=self.togglePicker, background_color=self.colors[3], background_normal='')) 

        self.layout.add_widget(Button(text='Update', pos=(W * 0.75, 70), size_hint=(.1, .05), on_press=self.renderThread.update))  

        return self.layout

    def _draw(self, data):
        img = Image.fromarray(data, 'RGB')
        imgBytes = BytesIO()
        img.save(imgBytes, format='png')
        imgBytes.seek(0)
        self.display.texture = CoreImage(BytesIO(imgBytes.read()), ext='png').texture
        
        Clock.schedule_once(partial(self.do_blit, img.tobytes(), W, H))

    def do_blit(self, buf, w, h, dt):
        texture = Texture(0, 0, 0).create(size=(w, h), colorfmt="bgr")
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.display.texture = texture
        self.updating = False

    def togglePicker(self, button):

        if button.text == 'Close':
            color = self.picker.color
            #color = np.array(color[0:3]) * 255
            self.colors[int(self.pickingColor) - 1] = (np.array(color[0:3]) * 255).astype(int)
            button.background_color = color

            self.layout.remove_widget(self.picker)

            button.text = 'Pick Color ' + self.pickingColor
            self.pickingColor = False
            return
        
        if self.pickingColor:
            return

        self.pickingColor = button.text[-1:]
        button.text = "Close"

        self.picker = ColorPicker()
        self.layout.add_widget(self.picker)

    def updateRange(self, slider, value):
        self.ranges[int(slider.ids["idx"])] = value



def main():
    app = MyApp()
    thread = RenderThread(app)
    app.renderThread = thread

    Window.size = (W, H * 1.3)

    app.run()


if __name__ == '__main__':
    main()


