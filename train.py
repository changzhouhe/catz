from keras.layers import Conv2D, UpSampling2D, MaxPooling2D,SimpleRNN,GRU,LSTM,Input,Lambda,ConvLSTM2D,BatchNormalization,Reshape,Concatenate,Permute,Conv1D,Add,Flatten,TimeDistributed
from keras.models import Sequential,Model,load_model
from keras.callbacks import Callback
import random
import glob
import wandb
from wandb.keras import WandbCallback
import subprocess
import os
from PIL import Image
import numpy as np
from keras import backend as K
#import pysnooper


run = wandb.init(project='catz')
config = run.config

config.num_epochs = 20 #30
config.batch_size = 32
config.img_dir = "images"
config.height = 96
config.width = 96

val_dir = 'catz/test'
train_dir = 'catz/train'

# automatically get the data if it doesn't exist
if not os.path.exists("catz"):
	print("Downloading catz dataset...")
	subprocess.check_output(
		"curl https://storage.googleapis.com/wandb/catz.tar.gz | tar xz", shell=True)

'''
class ImageCallback(Callback):
	def on_epoch_end(self, epoch, logs):
		validation_X, validation_y = next(
		my_generator(15, val_dir))
		output = self.model.predict(validation_X)
		wandb.log({
			"input": [wandb.Image(np.concatenate(np.split(c, 5, axis=2), axis=1)) for c in validation_X],
			"output": [wandb.Image(np.concatenate([validation_y[i], o], axis=1)) for i, o in enumerate(output)]
		}, commit=False)


def my_generator(batch_size, img_dir):
	"""A generator that returns 5 images plus a result image"""
	cat_dirs = glob.glob(img_dir + "/*")
	counter = 0
	while True:
		input_images = np.zeros((batch_size, config.width, config.height, 3 * 5))
		output_images = np.zeros((batch_size, config.width, config.height, 3))
		random.shuffle(cat_dirs)
		if ((counter+1)*batch_size >= len(cat_dirs)):
			counter = 0
		for i in range(batch_size):
			input_imgs = glob.glob(cat_dirs[counter + i] + "/cat_[0-5]*")
			imgs = [Image.open(img) for img in sorted(input_imgs)]
			input_images[i] = np.concatenate(imgs, axis=2)
			output_images[i] = np.array(Image.open(	cat_dirs[counter + i] + "/cat_result.jpg"))
		yield (input_images, output_images)
		counter += batch_size
'''
'''
model = Sequential()
model.add(Conv2D(32, (3, 3), activation='relu', padding='same',input_shape=(config.height, config.width, 5 * 3)))
model.add(MaxPooling2D(2, 2))
model.add(Conv2D(32, (3, 3), activation='relu', padding='same'))
model.add(UpSampling2D((2, 2)))
model.add(Conv2D(3, (3, 3), activation='relu', padding='same'))
'''
class ImageCallback(Callback):
	def on_epoch_end(self, epoch, logs):
		validation_X, validation_y = next(
		my_generator(15, val_dir))
		output = self.model.predict(validation_X)
		wandb.log({
			"input": [wandb.Image(np.concatenate(c, axis=1)) for c in validation_X],
			"output": [wandb.Image(np.concatenate([validation_y[i], o], axis=1)) for i, o in enumerate(output)]
		}, commit=False)

#@pysnooper.snoop()		
def my_generator(batch_size, img_dir):
	"""A generator that returns 5 images plus a result image"""
	cat_dirs = glob.glob(img_dir + "/*")
	counter = 0
	while True:
		input_images = np.zeros((batch_size, 5, config.width, config.height, 3))
		output_images = np.zeros((batch_size, config.width, config.height, 3))
		random.shuffle(cat_dirs)
		if ((counter+1)*batch_size >= len(cat_dirs)):
			counter = 0
		for i in range(batch_size):
			input_imgs = glob.glob(cat_dirs[counter + i] + "/cat_[0-5]*")
			imgs = [np.array(Image.open(img)) for img in sorted(input_imgs)]
			input_images[i] = (imgs) #np.concatenate(imgs, axis=0)
			output_images[i] = np.array(Image.open(	cat_dirs[counter + i] + "/cat_result.jpg"))
		yield (input_images, output_images)
		counter += batch_size

height=96#config.height		
width=96#config.width
new_height=height//8
new_width=width//8
channels=3
frames_num=5
filters_num=2


inputs = Input(shape=(5, height,width,channels), dtype='float32')
print(inputs.shape)

tmp_frame = TimeDistributed(Conv2D(32, (3, 3), activation='relu', padding='same'))(inputs)
print(tmp_frame.shape)
tmp_frame = TimeDistributed(MaxPooling2D(2, 2))(tmp_frame)
tmp_frame = TimeDistributed(Conv2D(16, (3, 3), activation='relu', padding='same'))(tmp_frame)
tmp_frame = TimeDistributed(MaxPooling2D(2, 2))(tmp_frame)
tmp_frame = TimeDistributed(Conv2D(3, (3, 3), activation='relu', padding='same'))(tmp_frame)
tmp_frame = TimeDistributed(MaxPooling2D(2, 2))(tmp_frame)
tmp_frame = Reshape((5,new_height*new_width*3))(tmp_frame)
x=GRU(new_height*new_width*3,return_sequences=False,dropout=0.4, recurrent_dropout=0.2,)(tmp_frame)
x=Reshape((new_height,new_width,channels))(x)
print(x.shape)
x=UpSampling2D((8,8))(x)


orig_img=Lambda(lambda x: x[:,4,:,:,:])(inputs)
output=Add()([orig_img,x])
print(output.shape)
model = Model(inputs=inputs, outputs=output)


def perceptual_distance(y_true, y_pred):
	rmean = (y_true[:, :, :, 0] + y_pred[:, :, :, 0]) / 2
	r = y_true[:, :, :, 0] - y_pred[:, :, :, 0]
	g = y_true[:, :, :, 1] - y_pred[:, :, :, 1]
	b = y_true[:, :, :, 2] - y_pred[:, :, :, 2]

	return K.mean(K.sqrt((((512+rmean)*r*r)/256) + 4*g*g + (((767-rmean)*b*b)/256)))

#@pysnooper.snoop('./mydebugfile.log')
def loss_perceptual_distance(y_true, y_pred):
	#print(y_pred.get_shape())
	rmean = (y_true[:, :, :, 0] + y_pred[:, :, :, 0]) / 2
	r = y_true[:, :, :, 0] - y_pred[:, :, :, 0]
	g = y_true[:, :, :, 1] - y_pred[:, :, :, 1]
	b = y_true[:, :, :, 2] - y_pred[:, :, :, 2]
	tmp=K.sqrt(K.maximum((((512+rmean)*r*r)/256) + 4*g*g + (((767-rmean)*b*b)/256),1e-16))
	return K.mean(tmp) #K.mean(K.sqrt((((512+rmean)*r*r)/256) + 4*g*g + (((767-rmean)*b*b)/256)))
	
model.compile(optimizer='adam', loss=loss_perceptual_distance, metrics=[perceptual_distance])
#model.compile(optimizer='adam', loss='mse', metrics=[perceptual_distance])
#model=load_model("./wandb/run-20190506_024007-jaiyr1tb/model-best.h5",custom_objects={'perceptual_distance':perceptual_distance})
#print(model.summary())


model.fit_generator(my_generator(config.batch_size, train_dir),
                    steps_per_epoch=len(glob.glob(train_dir + "/*")) // config.batch_size,
                    epochs=config.num_epochs, callbacks=[ImageCallback(), WandbCallback()],
    validation_steps=len(glob.glob(val_dir + "/*")) // config.batch_size,
    validation_data=my_generator(config.batch_size, val_dir))
'''

model.fit_generator(my_generator(config.batch_size, train_dir),
                    steps_per_epoch=3,
                    epochs=config.num_epochs, callbacks=[ImageCallback(), WandbCallback()],
    validation_steps=1,
    validation_data=my_generator(config.batch_size, val_dir))
'''
