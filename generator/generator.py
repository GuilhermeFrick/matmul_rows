import argparse
import math
import warnings
from utils import *
import os


def main(args):

    # print(config_yaml)
    
    config_yaml = write_config_yaml(args['tasks'])
    write_file("../config", "yaml", config_yaml)
    matrix_mult_std, matrix_size = write_h(config['vector_size'], config['tasks'], config['order_by'])
    write_file("../matrix_mult", "h", matrix_mult_std)
    for i in range(args['tasks']):
        if i == 0:
            master = write_master(config['tasks'])
            write_file("../master", "c", master)
        else:
            if i < 10:
                worker = write_workers(i, config['tasks'])
                write_file(f"../worker0{i}", "c", worker)
            else:
                worker = write_workers(i, config['tasks'])
                write_file(f"../worker{i}", "c", worker)


    print(f"Generated two {matrix_size}x{matrix_size} matrices")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MapReduce generator")
    parser.add_argument("-t", "--tasks", type=int, metavar='', required=True, help="number of tasks (must be power of 2)")
    parser.add_argument("-s", "--vector-size", type=int, metavar='', required=True, help="vector size")
    parser.add_argument("-o", "--order-by", type=str, metavar='', 
                        choices=["ascending", "descending", "random", "asc", "desc", "rand"],
                        required=True, help="vector ordenation: ascending, decending or random")
    config = vars(parser.parse_args())

    if config['vector_size']/config['tasks'] > 128:
        # raise argparse.ArgumentTypeError('Vector size is greater than message payload size')
        warnings.warn('Vector size is greater than message payload size')
    
    if config['vector_size'] < 1:
        raise argparse.ArgumentTypeError('Vector size must be greater than 0')

    if config['tasks'] < 2:
        raise argparse.ArgumentTypeError('Number of tasks must include at least one worker')

    if config['vector_size'] % (config['tasks'] - 1) != 0:
        raise argparse.ArgumentTypeError(
            'Matrix size must be divisible by the number of workers (tasks - 1)'
        )

    if(not(math.log2(config['tasks']).is_integer())):
        raise argparse.ArgumentTypeError('Number of tasks must be power of 2')

    # print(config)

    dir_name = "../"
    for item in os.listdir(dir_name):
        if item.endswith(".c"):
            os.remove(os.path.join(dir_name, item))
        if item.endswith(".h"):
            os.remove(os.path.join(dir_name, item))
        if item.endswith(".yaml"):
            os.remove(os.path.join(dir_name, item))

    main(config)
