import os


def remove_migration_files(path):
    for root, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            if dirname == 'migrations':
                dir_path = os.path.realpath(os.path.join(root, dirname))
                for filename in os.listdir(dir_path):
                    if not '__init__' in filename:
                        file_path = os.path.join(dir_path, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                print(file_path)
                                os.unlink(file_path)
                        except Exception as e:
                            print('Failed to delete %s. Reason: %s' % (file_path, e))
            # remove_empty_dir(os.path.realpath(os.path.join(root, dirname)))


if __name__ == '__main__':
    cwd = os.getcwd()
    print(cwd)
    remove_migration_files(cwd)
