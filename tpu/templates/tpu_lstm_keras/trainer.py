# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import argparse
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import LSTM


def build_model():
    inputs = tf.keras.Input(shape=(5, 3))
    encoded = tf.keras.layers.LSTM(10)(inputs)
    outputs = tf.keras.layers.Dense(1, activation=tf.nn.sigmoid)(encoded)

    model = tf.keras.Model(inputs=inputs, outputs=outputs)

    return model


def make_data():
    # This needs to be divisible by the number of towers/cores on the TPU.
    data_size = 128
    sequences = np.random.random((data_size, 5, 3))
    labels = np.random.randint(0, 2, size=(data_size,))

    return sequences, labels


def main(args):
    model = build_model()

    if args.use_tpu:
        # distribute over TPU cores
        # Note: This requires TensorFlow 1.11
        tpu_cluster_resolver = tf.contrib.cluster_resolver.TPUClusterResolver(args.tpu)
        strategy = tf.contrib.tpu.TPUDistributionStrategy(tpu_cluster_resolver)
        model = tf.contrib.tpu.keras_to_tpu_model(
            model, strategy=strategy)

    optimizer = tf.train.RMSPropOptimizer(learning_rate=0.05)
    loss_fn = tf.losses.log_loss
    model.compile(optimizer, loss_fn)

    sequences, labels = make_data()

    model.fit(sequences, labels, epochs=3)

    if not os.path.exists(args.model_dir):
        os.makedirs(args.model_dir)
    model.save(os.path.join(args.model_dir, 'model.hd5'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--model-dir',
        type=str,
        default='/tmp/tpu-template'
    )
    parser.add_argument(
        '--use-tpu',
        action='store_true'
    )
    parser.add_argument(
        '--tpu',
        default=None
    )

    args, _ = parser.parse_known_args()

    # colab.research.google.com specific
    import sys
    if 'google.colab' in sys.modules:
        import json
        import os
        from google.colab import auth

        # Authenticate to access GCS bucket
        auth.authenticate_user()

        # TODO(user): change this
        args.model_dir = 'gs://your-gcs-bucket'

        # When connected to the TPU runtime
        if 'COLAB_TPU_ADDR' in os.environ:
            tpu_grpc = 'grpc://{}'.format(os.environ['COLAB_TPU_ADDR'])

            args.tpu = tpu_grpc
            args.use_tpu = True

            # Upload credentials to the TPU
            with tf.Session(tpu_grpc) as sess:
                data = json.load(open('/content/adc.json'))
                tf.contrib.cloud.configure_gcs(sess, credentials=data)

    main(args)
