"""
File name: neuron.py
Author: Jason Roger Marc Edmonds
Created: 17.11.26
Last modified: 17.11.26
Version: 0.5

Single neuron with two inputs, trained to classify points into two colours (0 = blue, 1 = red).

Usage from the UI:
    from engine.neuron import train, predict_grid

    weights, bias = train(2000, inputs, outputs)
    grid = predict_grid(weights, bias, 50, 50)

    inputs  : list of points [[x, y], ...], x and y between 0 and 1 (y = 0 at the bottom)
    outputs : colour of each point, 0 = blue, 1 = red
    grid    : grid[row][column], one number between 0 and 1 per cell, grid[0][0] = top left cell
              below 0.5 = blue, above 0.5 = red
"""
# ----------------------------------------------------------------------------------------------------------------------

import random
import math

# shift used to measure the derivatives, and size of the corrections at each round
STEP = 0.0001
LEARNING_RATE = 10

# ----------------------------------------------------------------------------------------------------------------------


def sigmoid(nb):
    """
    Squeezes any number between 0 and 1.
    :param nb: number to transform
    :return: 1 / (1 + e^(-nb))
    """
    return 1/(1+math.exp(-nb))


def predict(example, weights, bias):
    """
    The neuron's answer for a single point.
    :param example: inputs of one point, for instance [0.8, 0.7]
    :param weights: list of weights, one per input
    :param bias: bias of the neuron
    :return: number between 0 and 1 (close to 0 = blue, close to 1 = red)
    """
    # weighted sum of the inputs, plus the bias
    prediction = 0
    for input_index in range(len(weights)):
        prediction += example[input_index] * weights[input_index]
    prediction += bias

    return sigmoid(prediction)


def compute_error(examples, outputs, weights, bias):
    """
    Mean squared error of the neuron over all the points.
    :param examples: list of all the points
    :param outputs: expected colour of each point
    :param weights: list of weights to test, one per input
    :param bias: bias to test
    :return: mean error over all the points
    """
    total_error = 0

    for example_index in range(len(examples)):
        # gap between the neuron's answer and the expected colour, squared
        sigmoid_prediction = predict(examples[example_index], weights, bias)
        gap = sigmoid_prediction - outputs[example_index]
        total_error += gap * gap

    mean_error = total_error / len(examples)

    return mean_error


def difference(a, b):
    """
    :param a: first value
    :param b: value to subtract
    :return: a - b
    """
    return a - b


def derivative(difference, shift):
    """
    Derivative of the error from a measured difference.
    :param difference: error gap caused by the shift
    :param shift: shift used to compute the difference
    :return: the derivative of the error
    """
    return difference / shift


def compute_derivatives(inputs, outputs, weights, bias):
    """
    Measures the derivative of the error for each weight and for the bias, without modifying them.
    :param inputs: list of all the points
    :param outputs: expected colour of each point
    :param weights: list of the current weights
    :param bias: current bias
    :return: the current error, the list of the weight derivatives (one per weight), the bias derivative
    """
    base_error = compute_error(inputs, outputs, weights, bias)

    weight_derivatives = []
    for index in range(len(weights)):
        # shift a single weight on a copy, the real weights stay unchanged
        copy = weights.copy()
        copy[index] -= STEP
        reduced_weight_error = compute_error(inputs, outputs, copy, bias)

        reduced_weight_difference = difference(base_error, reduced_weight_error)
        weight_derivatives.append(derivative(reduced_weight_difference, STEP))

    # same measurement for the bias
    reduced_bias = bias - STEP
    reduced_bias_error = compute_error(inputs, outputs, weights, reduced_bias)
    reduced_bias_difference = difference(base_error, reduced_bias_error)
    bias_derivative = derivative(reduced_bias_difference, STEP)

    return base_error, weight_derivatives, bias_derivative


def train(iterations, inputs, outputs):
    """
    Trains a new neuron on the given points, starting from random weights and bias.
    :param iterations: number of training rounds (2000 is enough)
    :param inputs: list of points [[x, y], ...], between 0 and 1
    :param outputs: colour of each point, 0 = blue, 1 = red
    :return: the trained weights (list) and bias
    """
    # random initialisation between -1 and 1: one weight per input, plus a bias
    weights = []
    for index in range(len(inputs[0])):
        weights.append(random.uniform(-1, 1))
    bias = random.uniform(-1, 1)

    for rounds in range(iterations):
        # measure every derivative on the same state, then correct every setting
        base_error, weight_derivatives, bias_derivative = compute_derivatives(inputs, outputs, weights, bias)

        for index in range(len(weights)):
            weights[index] -= (LEARNING_RATE * weight_derivatives[index])
        bias -= (LEARNING_RATE * bias_derivative)

    return weights, bias


def predict_grid(weights, bias, nb_rows, nb_columns):
    """
    The neuron's answer for the centre of every cell of a grid covering the whole area.
    :param weights: trained weights
    :param bias: trained bias
    :param nb_rows: number of rows of the grid
    :param nb_columns: number of columns of the grid
    :return: grid[row][column], numbers between 0 and 1, grid[0][0] = top left cell
    """
    grid = []
    for row in range(nb_rows):
        row_values = []
        for column in range(nb_columns):
            # centre of the cell, between 0 and 1 (row 0 is at the top, but y = 0 is at the bottom)
            x = (column + 0.5)/nb_columns
            y = 1-(row + 0.5)/nb_rows
            row_values.append(predict([x,y], weights, bias))
        grid.append(row_values)
    return grid


# ----------------------------------------------------------------------------------------------------------------------

# quick test, only runs when this file is launched directly (not when the UI imports it)
if __name__ == "__main__":
    inputs = [[0.1, 0.2], [0.3, 0.1], [0.2, 0.5], [0.4, 0.3], [0.8, 0.7], [0.6, 0.9], [0.9, 0.4], [0.7, 0.6]]
    outputs = [0, 0, 0, 0, 1, 1, 1, 1]
    weights, bias = train(2000, inputs, outputs)
    grid = predict_grid(weights, bias, 5, 5)
    for row_values in grid:
        print([round(value, 2) for value in row_values])