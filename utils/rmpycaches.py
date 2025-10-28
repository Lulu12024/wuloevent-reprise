import logging
import os
import shutil

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def remove_empty_dirs(path):
    for root, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            if dirname == '__pycache__':
                dir_path = os.path.realpath(os.path.join(root, dirname))
                print(dir_path)
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
                except Exception as exc:
                    logger.exception(exc.__str__())
                    pass
            # remove_empty_dir(os.path.realpath(os.path.join(root, dirname)))


if __name__ == '__main__':
    cwd = os.getcwd()
    remove_empty_dirs(cwd)
