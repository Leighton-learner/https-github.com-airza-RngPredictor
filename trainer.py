import numpy as np
import pkg_resources
import tensorflow as tf
import kerastuner as kt
from tensorflow import keras
from components import residual_block,residual_transformer,residual_lstm
from tensorflow.keras import Input
import datetime
from extractor import get_data_from_file

LOG_STEPS = 5
IMPORT_COUNT = 2**19
TEST_COUNT = 2**14
START_BIT = 4
END_BIT = 8
BATCH_SIZE = 512

RNG_NAME = "xorshift128"
if "xorshift128plus" == RNG_NAME:
	PREV_COUNT = 2
elif "xorshift128" == RNG_NAME:
	PREV_COUNT = 4
LOSS_FUNCTION = 'mse'
METRIC_FUNCTION = 'binary_accuracy'

def build_model(hp):
	activation_function= lambda x: tf.keras.activations.relu(x, alpha=alpha)
	b_count = hp.Int("before",1,3)#
	a_count = 1
	key_dim = 16
	heads = 4
	inputs = Input(shape=(X.shape[1],X.shape[2]))
	i1 = inputs*2
	i2 = i1-1
	l = tf.keras.layers.GaussianNoise(rate)(i2)
	for i in range(b_count):
		l = residual_lstm(l,activation=activation_function)
	l = LSTM(256,activation=activation_function)(l)
	for i in range(a_count):
		l =  residual_transformer(l,heads,key_dim,1,activation=activation_function)
	outputSize = 1 if len(y.shape)==1 else y.shape[1]
	outLayer= Dense(outputSize)(l)
	out = outLayer*.5
	output = out+.5
	loss = LOSS_FUNCTION
	model =keras.Model(inputs=inputs,outputs=output,name="fuckler")
	beta_1=beta_2= .9#hp.Float("b1",.2,.9,sampling="log")
	opt = tf.keras.optimizers.Nadam(
		learning_rate=1e-3,#hp.Float("learning_rate",1e-7,1e-1,sampling="log"),
		beta_1=beta_1,
		beta_2=beta_2,
		epsilon=1e-07,
    )
	model.compile(optimizer=opt,loss=loss,metrics=[METRIC_FUNCTION])
	return model
class StopWhenDoneCallback(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
    	accuracy= logs['binary_accuracy']
    	if accuracy>.99:
    		self.model.stop_training = True
stopEarly = tf.keras.callbacks.EarlyStopping(
	monitor='binary_accuracy', min_delta=.001, patience=15, verbose=0, mode='auto', restore_best_weights=False
)
"""
Control how many outputs back the model should look.
If you are not sure, I would suggest
(Size of the RNG state in bits)/(Bits of output from the RNG).
If your RNG produces low entropy output, you
may need more past data-but I have no tested this.
"""
X,y=get_data_from_file(RNG_NAME+'.rng',IMPORT_COUNT,PREV_COUNT,start_bit=START_BIT,end_bit=END_BIT)
print(X.shape)
X_train = X[TEST_COUNT:]
X_test = X[:TEST_COUNT]
y_train = y[TEST_COUNT:]
y_test = y[:TEST_COUNT]
log_dir = "logs/"+RNG_NAME+"/START_%02d_END_%02d/"%(START_BIT,END_BIT) +datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1,write_graph=False,profile_batch=0)
tuner = kt.tuners.bayesian.BayesianOptimization(build_model,"val_loss",100,project_name="hp_"+RNG_NAME+"_START_%02d_END_%02d"%(START_BIT,END_BIT))
tuner.search(X_train, y_train,batch_size=BATCH_SIZE,verbose=0,epochs=30,validation_data=(X_test,y_test),callbacks=[tf.keras.callbacks.TerminateOnNaN(),StopWhenDoneCallback(),tensorboard_callback])
tuner.results_summary()
best_hps = tuner.get_best_hyperparameters(num_trials =3)[-1]
model = tuner.hypermodel.build(best_hps)
model.fit(X_train, y_train,batch_size=BATCH_SIZE,verbose=0,epochs=100,validation_data=(X_test,y_test),callbacks=[StopWhenDoneCallback(),tensorboard_callback])
results = model.evaluate(X_test, y_test, batch_size=BATCH_SIZE)
model.save_weights(RNG_NAME+"_START_%02d_END_%02d"%(START_BIT,END_BIT)+"_WEIGHTS")