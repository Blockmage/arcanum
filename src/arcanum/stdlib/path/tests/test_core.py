import os
from unittest.mock import patch

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.helpers import FakeStatResult

from arcanum.stdlib.path._core import Path
from arcanum.stdlib.path._exceptions import FsError


@pytest.mark.usefixtures('fs')
class TestPath:
    """Test suite for the `Path` class."""

    fs: FakeFilesystem

    @pytest.fixture(autouse=True)
    def _inject_fs(self, fs: FakeFilesystem) -> None:
        """Injects the fake filesystem as an instance attribute before each test."""

        self.fs = fs

    def test_init(self, fs: FakeFilesystem) -> None:
        """Test initialization of `Path`."""

        path = Path('/tmp/test')

        assert str(path) == '/tmp/test'
        assert path._path == '/tmp/test'

    def test_eq(self, fs: FakeFilesystem) -> None:
        """Test equality comparison."""

        path1 = Path('/tmp/test')
        path2 = Path('/tmp/test')
        path3 = Path('/tmp/other')

        assert path1 == path2
        assert path1 != path3

        assert str(path1) == '/tmp/test'
        assert str(path1) != '/tmp/other'

        assert path1 != 123
        assert path1 is not None

    def test_comparison_operators(self, fs: FakeFilesystem) -> None:
        """Test comparison operators."""

        path1 = Path('/a/path')
        path2 = Path('/b/path')

        assert path1 < path2
        assert path1 <= path2

        assert path2 > path1
        assert path2 >= path1

        assert path1 <= path1  # noqa: PLR0124
        assert path1 >= path1  # noqa: PLR0124

    def test_truediv(self, fs: FakeFilesystem) -> None:
        """Test division operator for path joining."""

        path = Path('/tmp')
        result = path / 'test'

        assert isinstance(result, Path)
        assert str(result) == os.path.join('/tmp', 'test')

    def test_properties(self, fs: FakeFilesystem) -> None:
        """Test basic properties."""

        fs.create_file('/test.txt')
        fs.create_dir('/testdir')
        fs.create_symlink('/testlink', '/test.txt')

        file_path = Path('/test.txt')
        dir_path = Path('/testdir')
        link_path = Path('/testlink')
        nonexistent_path = Path('/nonexistent')

        assert file_path.exists()
        assert dir_path.exists()
        assert link_path.exists()
        assert not nonexistent_path.exists()

        assert file_path.is_file()
        assert not dir_path.is_file()
        assert not link_path.is_file()
        assert not nonexistent_path.is_file()

        assert not file_path.is_dir()
        assert dir_path.is_dir()
        assert not link_path.is_dir()
        assert not nonexistent_path.is_dir()

        assert not file_path.is_symlink()
        assert not dir_path.is_symlink()
        assert link_path.is_symlink()
        assert not nonexistent_path.is_symlink()

        assert file_path.is_absolute()
        assert not file_path.is_relative()

        rel_path = Path('relative/path')

        assert not rel_path.is_absolute()
        assert rel_path.is_relative()

    def test_path_components(self, fs: FakeFilesystem) -> None:
        """Test path component properties."""

        path = Path('/tmp/test/file.txt')

        assert path.parent == Path('/tmp/test')
        assert path.name == 'file.txt'
        assert path.suffix == '.txt'
        assert path.stem == 'file'

        path = Path('/tmp/test/file')

        assert path.suffix == ''
        assert path.stem == 'file'

        path = Path('/tmp/test/file.tar.gz')

        assert path.suffix == '.gz'
        assert path.stem == 'file.tar'

    def test_drive_and_anchor(self, fs: FakeFilesystem) -> None:
        """Test drive and anchor properties."""

        path = Path('/tmp/test')

        assert path.drive == ''
        assert path.anchor == os.sep

        path = Path('relative/path')

        assert path.drive == ''
        assert path.anchor == ''

    def test_joinpath(self, fs: FakeFilesystem) -> None:
        """Test `joinpath` method."""

        path = Path('/tmp')
        result = path.joinpath('test', 'file.txt')

        assert isinstance(result, Path)
        assert str(result) == os.path.join('/tmp', 'test', 'file.txt')

    def test_with_name_and_suffix(self, fs: FakeFilesystem) -> None:
        """Test `with_name` and `with_suffix` methods."""

        path = Path('/tmp/test/file.txt')
        new_path = path.with_name('newfile.txt')

        assert isinstance(new_path, Path)
        assert str(new_path) == os.path.join('/tmp/test', 'newfile.txt')

        new_path = path.with_suffix('.md')

        assert isinstance(new_path, Path)
        assert str(new_path) == os.path.join('/tmp/test', 'file.md')

    def test_stat(self, fs: FakeFilesystem) -> None:
        """Test `stat` method with caching."""

        fs.create_file('/tmp/test.txt', contents='test content')
        path = Path('/tmp/test.txt')

        stat_result = path.stat()

        assert isinstance(stat_result, FakeStatResult)
        assert stat_result.st_size == len('test content')

    def test_resolve_and_absolute(self, fs: FakeFilesystem) -> None:
        """Test `resolve` and `absolute` methods."""

        fs.create_file('/tmp/test.txt')
        fs.create_symlink('/tmp/testlink', '/tmp/test.txt')

        rel_path = Path('relative/path')
        abs_path = rel_path.absolute()

        assert isinstance(abs_path, Path)
        assert abs_path.is_absolute()

        link_path = Path('/tmp/testlink')
        resolved_path = link_path.resolve()

        assert isinstance(resolved_path, Path)
        assert str(resolved_path) != str(link_path)

    def test_expanduser(self) -> None:
        """Test `expanduser` method."""

        home_path = Path('~/test')
        expanded_path = home_path.expanduser()

        assert isinstance(expanded_path, Path)
        assert str(expanded_path) == os.path.expanduser('~/test')

    def test_file_operations(self, fs: FakeFilesystem) -> None:
        """Test file read/write operations."""

        fs.create_file('/tmp/test.txt', contents='test content')
        path = Path('/tmp/test.txt')

        assert path.read_text() == 'test content'
        assert path.read_bytes() == b'test content'

        path.write_text('new content')
        assert path.read_text() == 'new content'

        path.write_bytes(b'binary content')
        assert path.read_bytes() == b'binary content'

    def test_directory_operations(self, fs: FakeFilesystem) -> None:
        """Test directory operations."""

        dir_path = Path('/tmp/newdir')
        dir_path.mkdir()

        assert os.path.isdir('/tmp/newdir')

        nested_dir_path = Path('/tmp/parent/child')
        nested_dir_path.mkdir(parents=True)

        assert os.path.isdir('/tmp/parent/child')

        fs.create_file('/tmp/parent/file1.txt')
        fs.create_file('/tmp/parent/file2.txt')

        parent_path = Path('/tmp/parent')
        children = list(parent_path.iterdir())

        assert len(children) == 3
        assert all(isinstance(child, Path) for child in children)

        empty_dir_path = Path('/tmp/empty')
        empty_dir_path.mkdir()
        empty_dir_path.rmdir()

        assert not os.path.exists('/tmp/empty')

    def test_file_manipulation(self, fs: FakeFilesystem) -> None:
        """Test file manipulation operations."""

        fs.create_file('/tmp/original.txt')

        new_file_path = Path('/tmp/newfile.txt')
        new_file_path.touch()

        assert os.path.exists('/tmp/newfile.txt')

        original_path = Path('/tmp/original.txt')
        renamed_path = original_path.rename('/tmp/renamed.txt')

        assert isinstance(renamed_path, Path)
        assert not os.path.exists('/tmp/original.txt')
        assert os.path.exists('/tmp/renamed.txt')

        fs.create_file('/tmp/target.txt', contents='target content')

        source_path = Path('/tmp/renamed.txt')
        replaced_path = source_path.replace('/tmp/target.txt')

        assert isinstance(replaced_path, Path)
        assert not os.path.exists('/tmp/renamed.txt')
        assert os.path.exists('/tmp/target.txt')

        file_to_remove = Path('/tmp/target.txt')
        file_to_remove.unlink()

        assert not os.path.exists('/tmp/target.txt')

    def test_glob_and_rglob(self) -> None:
        """Test `glob` and `rglob` methods."""

        base_path = Path(str(self.fs.root))

        self.fs.create_file(f'{base_path}/tmp/test1.txt')
        self.fs.create_file(f'{base_path}/tmp/test2.txt')
        self.fs.create_file(f'{base_path}/other.md')

        self.fs.create_dir(f'{base_path}/subdir')
        self.fs.create_file(f'{base_path}/subdir/test3.txt')

        with patch(
            'glob.glob',
            return_value=[
                f'{base_path}/tmp/test1.txt',
                f'{base_path}/tmp/test2.txt',
            ],
        ):
            txt_files = list(base_path.glob('*.txt'))

        assert len(txt_files) == 2
        assert all(isinstance(p, Path) for p in txt_files)
        assert all(p.suffix == '.txt' for p in txt_files)

        with patch(
            'glob.glob',
            return_value=[
                f'{base_path}/tmp/test1.txt',
                f'{base_path}/tmp/test2.txt',
                f'{base_path}/subdir/test3.txt',
            ],
        ):
            all_txt_files = list(base_path.rglob('*.txt'))

        assert len(all_txt_files) == 3
        assert all(isinstance(p, Path) for p in all_txt_files)
        assert all(p.suffix == '.txt' for p in all_txt_files)

    def test_chmod(self, fs: FakeFilesystem) -> None:
        """Test `chmod` method."""

        fs.create_file('/test.txt')
        path = Path('/test.txt')

        path.chmod(0o644)
        stat_result = os.stat('/test.txt')

        assert stat_result.st_mode & 0o777 == 0o644

    def test_samefile(self, fs: FakeFilesystem) -> None:
        """Test `samefile` method."""

        fs.create_file('/test.txt')
        fs.create_symlink('/testlink', '/test.txt')

        path1 = Path('/test.txt')
        path2 = Path('/test.txt')
        path3 = Path('/testlink')
        path4 = Path('/nonexistent')

        assert path1.samefile(path2)
        assert path1.samefile(path3)

        with pytest.raises(FileNotFoundError):
            path1.samefile(path4)

    def test_static_methods(self) -> None:
        """Test `cwd` and `home` methods."""

        cwd_path = Path.cwd()
        assert isinstance(cwd_path, Path)
        assert str(cwd_path) == os.getcwd()

        home_path = Path.home()
        assert isinstance(home_path, Path)
        assert str(home_path) == os.path.expanduser('~')

    def test_relative_to(self) -> None:
        """Test `relative_to` method."""

        path = Path('/test/file.txt')
        rel_path = path.relative_to('')

        assert isinstance(rel_path, Path)
        assert str(rel_path) == 'test/file.txt'

        with pytest.raises(FsError):
            path.relative_to('/other')

    def test_is_reserved(self) -> None:
        """Test `is_reserved` method."""

        con_path = Path('CON')
        assert con_path.is_reserved()

        normal_path = Path('normal.txt')
        assert not normal_path.is_reserved()
