#!/usr/bin/env python 

from __future__ import print_function, division

import logging
import theano
import theano.tensor as T
import cPickle as pickle

import numpy as np
import os


from PIL import Image
from blocks.main_loop import MainLoop
from blocks.model import AbstractModel
from blocks.config import config

FORMAT = '[%(asctime)s] %(name)-15s %(message)s'
DATEFMT = "%H:%M:%S"
logging.basicConfig(format=FORMAT, datefmt=DATEFMT, level=logging.INFO)

def scale_norm(arr):
    arr = arr - arr.min()
    scale = (arr.max() - arr.min())
    return arr / scale

def img_grid(arr, global_scale=True):
    N, height, width = arr.shape

    rows = int(np.sqrt(N))
    cols = int(np.sqrt(N))

    if rows*cols < N:
        cols = cols + 1

    if rows*cols < N:
        rows = rows + 1

    total_height = rows * height
    total_width  = cols * width

    if global_scale:
        arr = scale_norm(arr)

    I = np.zeros((total_height, total_width))

    for i in xrange(N):
        r = i // cols
        c = i % cols

        if global_scale:
            this = arr[i]
        else:
            this = scale_norm(arr[i])

        offset_y, offset_x = r*height, c*width
        I[offset_y:(offset_y+height), offset_x:(offset_x+width)] = this
    
    I = (255*I).astype(np.uint8)
    return Image.fromarray(I)

def generate_samples(p, subdir, output_size):
    if isinstance(p, AbstractModel):
        model = p
    else:
        print("Don't know how to handle unpickled %s" % type(p))
        return

    draw = model.get_top_bricks()[0]
    # reset the random generator
    del draw._theano_rng
    del draw._theano_seed
    draw.seed_rng = np.random.RandomState(config.default_seed)

    #------------------------------------------------------------
    logging.info("Compiling sample function...")

    n_samples = T.iscalar("n_samples")
    samples = draw.sample(n_samples)

    do_sample = theano.function([n_samples], outputs=samples, allow_input_downcast=True)

    #------------------------------------------------------------
    logging.info("Sampling and saving images...")

    samples = do_sample(16*16)
    #samples = np.random.normal(size=(16, 100, 28*28))

    n_iter, N, D = samples.shape

    samples = samples.reshape( (n_iter, N, output_size, output_size) )

    if(n_iter > 0):
        img = img_grid(samples[n_iter-1,:,:,:])
        img.save("{0}/sample.png".format(subdir))

    for i in xrange(n_iter):
        img = img_grid(samples[i,:,:,:])
        img.save("{0}/sample-{1:03d}.png".format(subdir, i))

    #with open("centers.pkl", "wb") as f:
    #    pikle.dump(f, (center_y, center_x, delta))
    os.system("convert -delay 5 -loop 1 {0}/sample-*.png {0}/samples.gif".format(subdir))

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("model_file", help="filename of a pickled DRAW model")
    parser.add_argument("--size", type=int,
                default=28, help="Output image size (width and height)")
    args = parser.parse_args()

    logging.info("Loading file %s..." % args.model_file)
    with open(args.model_file, "rb") as f:
        p = pickle.load(f)

    subdir = "sample"
    if not os.path.exists(subdir):
        os.makedirs(subdir)

    generate_samples(p, subdir, args.size)



