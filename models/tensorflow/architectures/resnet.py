# pylint: disable=too-many-arguments
# pylint: disable=not-context-manager
# pylint: disable=duplicate-code
# pylint: disable=anomalous-backslash-in-string
""" Contains TFResNet model class. """

import tensorflow as tf
from ..tf_model import TFModelCT
from ..layers import bn_conv3d


class TFResNet(TFModelCT):
    """ This class implements 3D ResNet architecture via tensorflow.

    Full description of similar 2D model architecture can be downloaded from here:
    https://arxiv.org/pdf/1512.03385v1.pdf

    Attributes
    ----------
    config : dict
        config dictionary from dataset pipeline
        see configuring model section of dataset module
        https://analysiscenter.github.io/dataset/intro/models.html.
    name : str
        name of the model, can be specified in config dict.
    units : tuple(int, int)
        number of units in two final dense layers before tensor with predicitons,
        can be specified in config dict.
    num_targets : int
        size of tensor with predicitons.
    dropout_rate : float
        probability of dropout, can be specified in config dict.

    NOTE
    ----
    This class is descendant of TFModel class from dataset.models.*.
    """

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config', {})
        self.num_targets = self.get_from_config('num_targets', 1)
        self.dropout_rate = self.get_from_config('dropout_rate', 0.35)
        super().__init__(*args, **kwargs)

    def identity_block(self, input_tensor, kernel_size, filters, name):
        """ The identity block is the block that has no conv layer at shortcut.

        First of all, 3D-convolution with (1, 1, 1) kernel size, batch normalization
        and relu activation is applied. Then the result flows into
        3D-convolution with (3, 3, 3) kernel size, batch normalization and
        relu activation. Finally, the result of previous convolution goes
        into 3D-convolution with (1, 1, 1) kernel size, batch normalization
        without activation and its output is summed with the input tensor
        and 'relu' activation is applied.
        Argument `filters` should be tuple(int, int, int) and specifies
        number of filters in first, second and third convolution correspondingly.
        Number of filters in third convolution must be the same as in the input
        tensor.

        Parameters
        ----------
        input_tensor : tf.Tensor
            input tensor.
        kernel_size : tuple(int, int, int)
            size of kernel along three dimensions for middle convolution operation in block.
        filters : tuple(int, int, int)
            number for filters in first, second and third 3D-convolution operations.
        name : str
            name of block that will be used as argument of of tf.variable_scope.

        Returns
        -------
        tf.Tensor
            output tensor.
        """
        filters1, filters2, filters3 = filters

        with tf.variable_scope(name):
            x = bn_conv3d(input_tensor, filters1, (1, 1, 1),
                          name='bn_conv_a', padding='same',
                          activation=tf.nn.relu,
                          is_training=self.is_training)

            x = bn_conv3d(x, filters2, kernel_size,
                          name='bn_conv_b', padding='same',
                          activation=tf.nn.relu,
                          is_training=self.is_training)

            x = bn_conv3d(x, filters3, (1, 1, 1),
                          name='bn_conv_c', padding='same',
                          activation=tf.identity,
                          is_training=self.is_training)

            output_tensor = tf.add(x, input_tensor)
            output_tensor = tf.nn.relu(output_tensor)
        return output_tensor

    def conv_block(self, input_tensor, kernel_size, filters, name, strides=(2, 2, 2)):
        """ Convolutional block that has a conv layer as shortcut.

        First of all, 3D-convolution with (1, 1, 1) kernel size, (2, 2, 2)-strides,
        batch normalization and 'relu' activation is applied. Then the result
        flows into 3D-convolution with (3, 3, 3) kernel size, batch normalization
        and 'relu' activation. Finally, the result of previous convolution goes
        into 3D-convolution with (1, 1, 1) kernel size, batch normalization
        without activation and its output is summed with the result
        of 3D-convolution with kernel_size=(1, 1, 1), strides=(2, 2, 2) and
        batch normalization of input_tensor. After that 'relu' activation
        is applied to the result of 'add' operation.
        Argument `filters` should be tuple(int, int, int) and specifies
        number of filters in first, second and third convolution correspondingly.

        Parameters
        ----------
        input_tensor : tf.Tensor
            input tensor.
        kernel_size : tuple(int, int, int)
            size of kernel along three dimensions for middle convolution operation in block.
        filters : tuple(int, int, int)
            number of filters in first, second, and third 3D-convolution operations.

        Returns
        -------
        tf.Tensor
            output tensor.
        """
        filters1, filters2, filters3 = filters

        with tf.variable_scope(name):
            x = bn_conv3d(input_tensor, filters1, (1, 1, 1),
                          name='bn_conv_a', padding='same',
                          activation=tf.nn.relu, strides=strides,
                          is_training=self.is_training)

            x = bn_conv3d(x, filters2, kernel_size,
                          name='bn_conv_b', padding='same',
                          activation=tf.nn.relu, is_training=self.is_training)

            x = bn_conv3d(x, filters3, (1, 1, 1),
                          name='bn_conv_c', padding='same',
                          activation=tf.nn.relu)

            shortcut = bn_conv3d(input_tensor, filters3, (1, 1, 1),
                                 strides=strides, name='bn_conv3d_shortcut',
                                 padding='same', activation=tf.identity,
                                 is_training=self.is_training)

            output_tensor = tf.add(x, shortcut)
            output_tensor = tf.nn.relu(output_tensor)
        return output_tensor

    def _build(self, *args, **kwargs):
        """ Build renset model implemented via tensorflow. """
        input_tensor = tf.placeholder(shape=(None, 32, 64, 64, 1), dtype=tf.float32, name='x')
        y_true = tf.placeholder(shape=(None, self.num_targets), dtype=tf.float32, name='targets')

        x = bn_conv3d(input_tensor, filters=32, kernel_size=(5, 3, 3),
                      name='initial_conv', padding='same',
                      is_training=self.is_training)

        x = tf.layers.max_pooling3d(x, pool_size=(3, 3, 3), strides=(2, 2, 2),
                                    name='initial_maxpool')

        x = self.conv_block(x, (3, 3, 3), [16, 16, 32], name='conv_1A', strides=(1, 1, 1))
        x = self.identity_block(x, (3, 3, 3), [16, 16, 32], name='identity_1B')
        x = self.identity_block(x, (3, 3, 3), [16, 16, 32], name='identity_1C')
        x = tf.layers.dropout(x, rate=self.dropout_rate, training=self.is_training)

        x = self.conv_block(x, (3, 3, 3), [24, 24, 64], name='conv_2A')
        x = self.identity_block(x, (3, 3, 3), [24, 24, 64], name='identity_2B')
        x = self.identity_block(x, (3, 3, 3), [24, 24, 64], name='identity_2C')
        x = self.identity_block(x, (3, 3, 3), [24, 24, 64], name='identity_2D')
        x = tf.layers.dropout(x, rate=self.dropout_rate, training=self.is_training)

        x = self.conv_block(x, (3, 3, 3), [48, 48, 128], name='conv_3A')
        x = self.identity_block(x, (3, 3, 3), [48, 48, 128], name='identity_3B')
        x = self.identity_block(x, (3, 3, 3), [48, 48, 128], name='identity_3C')

        x = self.identity_block(x, (3, 3, 3), [48, 48, 128], name='identity_3D')
        x = self.identity_block(x, (3, 3, 3), [48, 48, 128], name='identity_3E')
        x = self.identity_block(x, (3, 3, 3), [48, 48, 128], name='identity_3F')
        x = tf.layers.dropout(x, rate=self.dropout_rate, training=self.is_training)

        x = self.conv_block(x, (3, 3, 3), [64, 64, 196], name='conv_4A')
        x = self.identity_block(x, (3, 3, 3), [64, 64, 196], name='identity_4B')
        x = self.identity_block(x, (3, 3, 3), [64, 64, 196], name='identity_4C')

        z = tf.contrib.layers.flatten(x)

        z = tf.layers.dense(z, units=64, name='dense_64')
        z = tf.layers.batch_normalization(z, axis=-1, training=self.is_training)
        z = tf.nn.relu(z)

        z = tf.layers.dense(z, units=16, name='dense_16')
        z = tf.layers.batch_normalization(z, axis=-1, training=self.is_training)
        z = tf.nn.relu(z)

        z = tf.layers.dense(z, units=self.num_targets, name='dense_' + str(self.num_targets))
        z = tf.nn.sigmoid(z)

        y_pred = tf.identity(z, name='predictions')

        self.store_to_attr('y', y_true)
        self.store_to_attr('x', input_tensor)
        self.store_to_attr('y_pred', y_pred)