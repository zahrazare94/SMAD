from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import reader
import math
import os

os.environ['TF_CPP_MIN_LOG_LEVEL']='2'

import transformData as td
import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np

#starter_learning_rate = 0.30
#beta = 0.0
#layers = [32,16,8]

def layer(x, n_in, n_out):
    low = -4*np.sqrt(6.0/(n_in + n_out))
    high = 4*np.sqrt(6.0/(n_in + n_out))
    #w = tf.Variable(tf.random_uniform(shape=[n_in, n_out], minval=low, maxval=high, dtype=tf.float32))
    w = tf.Variable(tf.truncated_normal(shape=[n_in, n_out]))
    b = tf.Variable(tf.zeros([n_out]))
    return w, tf.matmul(x,w) + b, tf.sigmoid(tf.matmul(x,w) + b)


''' Differentiable approximation of the f-mesure performed by the model on a given dataset.
    Based on the article of Martin Jansche "Maximum Expected F-Measure Training of Logistic Regression Models"

    true_positive -> sum(sigmoid(gamma*logits)) for label = +1
    detected -> sum(sigmoid(gamma*logits))

    for gamma -> + infinity
'''
def f_mesure_approx(logits, labels, gamma):
    param = tf.constant([1,0], tf.float32,shape=[1,2])
    true_positive = tf.reduce_mean(tf.matmul(param, tf.reduce_sum(tf.multiply(labels,tf.nn.softmax(gamma*logits)),0,keep_dims=True),transpose_b=True))
    positive = tf.reduce_mean(tf.matmul(param, tf.reduce_sum(labels,0,keep_dims=True),transpose_b=True))
    detected = tf.reduce_mean(tf.matmul(param, tf.reduce_sum(tf.nn.softmax(gamma*logits),0,keep_dims=True),transpose_b=True))

    return 2*true_positive/(positive+detected)


def evaluate_model(logits, labels):
    true_positive = tf.cast(tf.equal(tf.argmax(logits,1) + tf.argmax(labels,1), 0), tf.float32)
    positive = tf.cast(tf.equal(tf.argmax(labels,1), 0), tf.float32)
    detected = tf.cast(tf.equal(tf.argmax(logits,1), 0), tf.float32)
    correct_prediction = tf.equal(tf.argmax(logits, 1), tf.argmax(labels,1))

    precision = tf.reduce_sum(true_positive)/tf.reduce_sum(detected)
    recall = tf.reduce_sum(true_positive)/tf.reduce_sum(positive)
    f_mesure = 2*precision*recall/(precision+recall)
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    return precision, recall, f_mesure, accuracy    

def test_model(x_train, y_train, x_valid, y_valid, layers, starter_learning_rate, beta, name = "yo", i=0):
    graph = tf.Graph()
    with graph.as_default():

        input_size = len(x_train[0]) #4
        output_size = len(y_train[0]) #2
        layers.append(output_size)

        # Input data. For the training data, we use a placeholder that will be fed
        # at run time with a training minibatch.
        x = tf.placeholder(tf.float32,[None,input_size])
        y_ = tf.placeholder(tf.float32,[None,output_size])


        # Construct model
        h = x
        logits = x
        regularizers = 0
        n_in = input_size
        for size in layers:
            w, logits, h = layer(h, n_in, size)
            regularizers = regularizers + tf.nn.l2_loss(w)
            n_in = size

        # Loss function with L2 Regularization
        loss = 1 - f_mesure_approx(logits, y_, 2)
        loss = tf.reduce_mean(loss + beta * regularizers)
        

        # Learning mecanism 
        global_step = tf.Variable(0, trainable=False)
        learning_rate = tf.train.exponential_decay(starter_learning_rate, global_step,
                                               500, 0.9, staircase=True)
        # Passing global_step to minimize() will increment it at each step.
        learning_step = (
            tf.train.GradientDescentOptimizer(learning_rate)
            .minimize(loss, global_step=global_step)
        )

        # Predictions for the training
        train_prediction = tf.nn.softmax(logits)

        precision, recall, f_mesure, accuracy = evaluate_model(logits, y_)



    num_steps = 2000
    losses = []
    losses1 = []
    fm = []
    lrates = []
    bestLossStep = 0
    bestLoss = 100
    bestFMStep = 0
    bestFM = 0

    with tf.Session(graph=graph) as session:
        session.run(tf.global_variables_initializer())
        #print("Initialized")

        for step in range(num_steps):
            batch_data, batch_labels = td.shuffle(x_train, y_train)
            feed_dict = {x: batch_data, y_: batch_labels}

            session.run(learning_step, feed_dict=feed_dict)
            l1 = session.run(loss, feed_dict={x:x_train, y_:y_train})
            l, f, lr = session.run([loss, f_mesure, learning_rate], feed_dict={x:x_valid, y_:y_valid})
            losses1.append(l1)
            losses.append(l)
            fm.append(f)
            lrates.append(lr)

            #print(step)
            if l < bestLoss:
                bestLoss = l
                bestLossStep = step

            if f > bestFM:
                bestFM = f
                bestFMStep = step

        precision, recall, f_mesure, accuracy = session.run([precision, recall, f_mesure, accuracy], feed_dict={x: x_valid, y_: y_valid})
        F = open("results.txt", 'a')
        F.write(str(name) + ":"+str(f_mesure)+ " "+str(bestFM)+"\n")
        F.close()

        plt.figure(i)
        plt.plot(range(num_steps), losses, range(num_steps), losses1, range(num_steps), fm, range(num_steps), lrates)
        plt.savefig("./data/fig/"+name+".png")






'''
graph = tf.Graph()
with graph.as_default():

    instances , labels = reader.constructDataset2()
    dataset_x , dataset_y = td.shuffle(instances , labels)

    validSet_start_idx = int(math.ceil(len(dataset_x)*0.7))

    x_train = dataset_x[:validSet_start_idx,:]
    y_train = dataset_y[:validSet_start_idx,:]
    x_valid = dataset_x[validSet_start_idx:,:]
    y_valid = dataset_y[validSet_start_idx:,:]

    nonZeroTotal = np.nonzero(dataset_y[:,0])[0].size
    nonZeroTrain = np.nonzero(y_train[:,0])[0].size
    nonZeroValid = np.nonzero(y_valid[:,0])[0].size

    print('nonzero :', nonZeroTotal, nonZeroTrain, nonZeroValid)

    input_size = len(x_train[0]) #4
    output_size = len(y_train[0]) #2
    layers.append(output_size)

    # Input data. For the training data, we use a placeholder that will be fed
    # at run time with a training minibatch.
    x = tf.placeholder(tf.float32,[None,input_size])
    y_ = tf.placeholder(tf.float32,[None,output_size])


    # Construct model
    # Construct model
    h = x
    logits = x
    regularizers = 0
    n_in = input_size
    for size in layers:
        w, logits, h = layer(h, n_in, size)
        regularizers = regularizers + tf.nn.l2_loss(w)
        n_in = size


    # Loss function with L2 Regularization
    loss = 1 - f_mesure_approx(logits, y_, 2)
    loss = tf.reduce_mean(loss + beta * regularizers)
    

    # Learning mecanism 
    global_step = tf.Variable(0, trainable=False)
    learning_rate = tf.train.exponential_decay(starter_learning_rate, global_step,
                                           400, 0.9, staircase=True)
    # Passing global_step to minimize() will increment it at each step.
    learning_step = (
        tf.train.GradientDescentOptimizer(learning_rate)
        .minimize(loss, global_step=global_step)
    )

    # Predictions for the training
    train_prediction = tf.nn.softmax(logits)

    precision, recall, f_mesure, accuracy = evaluate_model(logits, y_)



num_steps = 4000
losses = []
fm = []
lrates = []
bestLossStep = 0
bestLoss = 100
bestFMStep = 0
bestFM = 0

with tf.Session(graph=graph) as session:
    session.run(tf.global_variables_initializer())
    print("Initialized")

    for step in range(num_steps):
        batch_data, batch_labels = td.shuffle(x_train, y_train)
        feed_dict = {x: batch_data, y_: batch_labels}

        session.run(learning_step, feed_dict=feed_dict)
        l, f, lr = session.run([loss, f_mesure, learning_rate], feed_dict={x:x_valid, y_:y_valid})
        losses.append(l)
        fm.append(f)
        lrates.append(lr)

        if l < bestLoss:
            bestLoss = l
            bestLossStep = step

        if f > bestFM:
            bestFM = f
            bestFMStep = step

    precision, recall, f_mesure, accuracy = session.run([precision, recall, f_mesure, accuracy], feed_dict={x: x_valid, y_: y_valid})
    print('Precision :', precision)
    print('Recall :', recall)
    print('F-Mesure :', f_mesure)
    print('Accuracy :', accuracy)
    print('\n')
    print('Best loss :',bestLoss,' at step :',bestLossStep)
    print('Best f-mesure :',bestFM,' at step :',bestFMStep)

    plt.plot(range(num_steps), losses,range(num_steps), fm, range(num_steps), lrates)
    plt.show()'''

if __name__ == "__main__":
    instances , labels = reader.constructDataset2()
    dataset_x , dataset_y = td.shuffle(instances , labels)
    dataset_x = td.standardizeData(dataset_x)

    validSet_start_idx = int(math.ceil(len(dataset_x)*0.7))

    x_train = dataset_x[:validSet_start_idx,:]
    y_train = dataset_y[:validSet_start_idx,:]
    x_valid = dataset_x[validSet_start_idx:,:]
    y_valid = dataset_y[validSet_start_idx:,:]

    nonZeroTotal = np.nonzero(dataset_y[:,0])[0].size
    nonZeroTrain = np.nonzero(y_train[:,0])[0].size
    nonZeroValid = np.nonzero(y_valid[:,0])[0].size

    print('nonzero :', nonZeroTotal, nonZeroTrain, nonZeroValid)

    starter_learning_rate = 0.26
    beta = 0.0
    layers = [32,16,8]

    test_model(x_train, y_train, x_valid, y_valid, layers, starter_learning_rate, beta)

    '''starter_learning_rate = 0.22
    beta = 0.0
    layers = [32,16,8]


    systems = [
        'android-frameworks-opt-telephony',
        'android-frameworks-sdk',
        'android-frameworks-tool-base',
        'android-platform-support',
        'apache-ant',
        'apache-cassandra',
        'apache-commons-codec',
        'apache-commons-io',
        'apache-commons-lang',
        'apache-commons-logging',
        'apache-derby',
        'apache-ivy',
        'apache-karaf',
        'apache-log4j',
        'apache-pig',
        'apache-struts',
        'apache-tomcat',
        'eclipse-jdt-core',
        'google-guava',
        'jedit',
        'mongodb'
    ]

    for i in range(len(systems)):
        sys = list(systems)
        sys.pop(i)
        for j in range(3):
            print(i,"-",j)
            x_valid, y_valid = reader.system2Data(systems[i])


            x_train = np.empty(shape=[0,4])
            y_train = np.empty(shape=[0,2])
            for system in sys:
                systemInstances , systemLabels = reader.system2Data(system)

                x_train = np.concatenate((x_train, systemInstances), axis=0)
                y_train = np.concatenate((y_train, systemLabels), axis=0)

            idx = len(x_train)
            x_train = np.concatenate((x_train, x_valid), axis=0)
            x_train = td.standardizeData(x_train)

            x_valid = x_train[idx:,:]
            x_train = x_train[:idx,:]


            test_model(x_train, y_train, x_valid, y_valid, layers, starter_learning_rate, beta, systems[i], i)'''