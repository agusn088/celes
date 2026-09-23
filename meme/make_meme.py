from PIL import Image, ImageDraw, ImageFont
import numpy as np
im=Image.open('original.jpg').convert('RGB')
a=np.asarray(im).astype(int); L=a.mean(2)
sub=a[950:975,750:825]; m=(L[950:975,750:825]>90)
tc=tuple(int(v) for v in np.median(sub[m],0)); print('time color',tc)
BUB=(37,40,45); TXT=(230,231,234)
f=ImageFont.truetype('fonts/Roboto-400.ttf',43)
ft=ImageFont.truetype('fonts/Roboto-400.ttf',29)
d=ImageDraw.Draw(im)
# bubble 3: erase old text, keep bubble + its time
d.rectangle((158,760,925,886),fill=BUB); d.rectangle((925,760,1012,866),fill=BUB)
off=f.getbbox('C')[1]
d.text((170,773-off),'Con esa plata comprábamos 5 kilos',font=f,fill=TXT)
d.text((170,825-off),'de milanesas y comíamos todo el mes',font=f,fill=TXT)
# bubble 4: redraw wider
t4='QUE HAGO YO CON ESTO? LO EMPANO?'
w=f.getlength(t4); tx=169+w+76; tw=ft.getlength('16:14'); R=int(tx+tw+20)
print('bubble4 right',R)
d.rounded_rectangle((140,902,R,1040),radius=22,fill=BUB)
d.text((169,932-f.getbbox('Q')[1]),t4,font=f,fill=TXT)
d.text((tx,952-ft.getbbox('1')[1]),'16:14',font=ft,fill=tc)
from PIL import ImageFilter
for box in [(150,758,1015,890),(140,905,1116,993)]:
    im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(0.7)),box[:2])
im.save('meme-milanesas.png')
