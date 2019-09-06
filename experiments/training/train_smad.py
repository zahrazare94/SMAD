from context import ROOT_DIR, nnUtils, md

import tensorflow        as tf
import numpy             as np
import matplotlib.pyplot as plt

import argparse
import os

os.environ['TF_CPP_MIN_LOG_LEVEL']='2'

training_systems = {
	'android-frameworks-opt-telephony',
	'android-platform-support',
	'apache-ant',
	'lucene',
	'apache-tomcat',
	'argouml',
	'jedit',
	'xerces-2_7_0'
}

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("antipattern", help="Either 'god_class' or 'feature_envy'")
	parser.add_argument("test_system", help="The name of the system to be used for testing.\n Hence, the training will be performed using all the systems except this one.")
	parser.add_argument("-lr", type=float, help="The learning rate to be used for training.")
	parser.add_argument("-beta", type=float, help="The L2 regularization scale to be used for training.")
	parser.add_argument("-gamma", type=int, help="Learning hyper-parameter, used to compute the network's loss function (to compute a differentiable approximation of the Matheus Correlation Coefficient)")
	parser.add_argument('-dense_sizes', nargs='+', type=int, help="The sizes of each (dense) hidden layer in the network.")
	parser.add_argument("-n_net", type=int, default=10, help="The number of distinct networks to be trained and saved.")
	parser.add_argument("-n_step", type=int, default=200, help="The number of training steps.")
	parser.add_argument("-decay_step", type=int, default=100, help="The number of training steps after which the learning rate is decayed")
	parser.add_argument("-lr_decay", type=float, default=0.5, help="The factor by which the learning rate is multiplied every 'decay_step' steps")
	return parser.parse_args()

# Train a single network
def train(session, model, x_train, y_train, x_test, y_test, num_step, start_lr, beta, gamma, decay_step, lr_decay):
	learning_rate = start_lr
	losses_train = []
	losses_test  = []
	for step in range(num_step):
		# Learning rate decay
		if (step%decay_step == 0) & (step>0):
			learning_rate = learning_rate*lr_decay

		feed_dict_train = {
					model.input_x: x_train,
					model.input_y: y_train,
					model.learning_rate:learning_rate,
					model.beta:beta,
					model.gamma: gamma}

		session.run(model.learning_step, feed_dict=feed_dict_train)

		loss_train = session.run(model.loss, feed_dict={model.input_x:x_train, model.input_y:y_train, model.gamma: gamma})
		loss_test  = session.run(model.loss, feed_dict={model.input_x:x_test, model.input_y:y_test, model.gamma: gamma})
		losses_train.append(loss_train)
		losses_test.append(loss_test)
	return losses_train, losses_test

if __name__ == "__main__":
	args = parse_args()

	# Remove the test system from the training set and build dataset
	training_systems.remove(args.test_system)
	x_train, y_train = nnUtils.build_dataset(args.antipattern, training_systems)
	x_test, y_test = nnUtils.build_dataset(args.antipattern, [args.test_system])

	# Create model
	model = md.SMAD(
		shape=args.dense_sizes, 
		input_size=x_train.shape[-1])

	# To save and restore a trained model
	saver = tf.train.Saver(max_to_keep=args.n_net)

	# Train several neural networks
	all_losses_train = []
	all_losses_test  = []
	with tf.Session() as session:
		for i in range(args.n_net):
			print('Training Neural Network :' + str(i+1))

			# Initialize the variables of the TensorFlow graph.
			session.run(tf.global_variables_initializer())

			# Train the model
			losses_train, losses_test = train(
				session=session,
				model=model,
				x_train=x_train,
				y_train=y_train,
				x_test=x_test,
				y_test=y_test,
				num_step=args.n_step,
				start_lr=args.lr,
				beta=args.beta,
				gamma=args.gamma,
				decay_step=args.decay_step,
				lr_decay=args.lr_decay)

			all_losses_train.append(losses_train)
			all_losses_test.append(losses_test)

			# Save the model
			saver.save(sess=session, save_path=nnUtils.get_save_path('smad', args.antipattern, args.test_system, i))


	# Compute the ensemble prediction on the test system
	ensemble_prediction = nnUtils.ensemble_prediction(
		model=model, 
		save_paths=[nnUtils.get_save_path('smad', args.antipattern, args.test_system, i) for i in range(args.n_net)], 
		input_x=x_test)

	# Print Ensemble performances
	print("\nPerformances on " + args.test_system + ": ")
	print('Precision: ' + str(nnUtils.precision(ensemble_prediction, y_test)))
	print('Recall   : ' + str(nnUtils.recall(ensemble_prediction, y_test)))
	print('F-Mesure : ' + str(nnUtils.f_measure(ensemble_prediction, y_test)))
	print('MCC      : ' + str(nnUtils.mcc(ensemble_prediction, y_test)))

	# Plot learning curves
	nnUtils.plot_learning_curves(all_losses_train, all_losses_test)
