from __future__ import division

import tensorflow as tf


class SMAD(object):
	def __init__(self, shape, input_size):

		# Placeholders for instances and labels
		self.input_x = tf.placeholder(tf.float32,[None, input_size], name="input_x")
		self.input_y = tf.placeholder(tf.float32,[None, 1], name="input_y")
		
		# Placeholders for training parameters
		self.learning_rate = tf.placeholder(tf.float32, name="learning_rate")
		self.beta          = tf.placeholder(tf.float32, name="beta")

		# L2 regularization & initialization
		l2_reg = tf.contrib.layers.l2_regularizer(scale=self.beta)
		xavier = tf.contrib.layers.xavier_initializer()

		# Hidden layers
		h_in = self.input_x
		for size in shape:
			with tf.name_scope("hidden-%s" % size):
				h_in = tf.layers.dense(
					inputs=h_in,
					units=size,
					activation=tf.tanh,
					kernel_initializer=xavier,
					kernel_regularizer=l2_reg,
					bias_regularizer=l2_reg)

		# Output layer
		with tf.name_scope("output"):
			self.logits = tf.layers.dense(
				inputs=h_in,
				units=1,
				kernel_initializer=xavier,
				kernel_regularizer=l2_reg,
				bias_regularizer=l2_reg)
			self.inference = tf.nn.sigmoid(self.logits)

		# Loss function
		with tf.name_scope("loss"):
			self.loss = loss(self.logits, self.input_y)
			l2_loss = tf.losses.get_regularization_loss()
			loss_reg = self.loss + l2_loss

		# Learning mechanism
		self.learning_step = tf.train.GradientDescentOptimizer(self.learning_rate).minimize(loss_reg)


def loss(logits, labels):
	''' 
	This function implements the Differentiable approximation of the f-measure from:
	Martin Jansche (2005):
	    [Maximum Expected F-Measure Training of Logistic Regression Models]

	true_positive:  sum(sigmoid(gamma*logits)) for label = +1
	detected: sum(sigmoid(gamma*logits))
	gamma > 0
	'''
	gamma = 4

	true_positive = tf.reduce_sum(tf.multiply(labels, tf.nn.sigmoid(gamma*logits)))
	positive = tf.reduce_sum(labels)
	detected = tf.reduce_sum(tf.nn.sigmoid(gamma*logits))

	return 1 - 2*true_positive/(positive+detected)