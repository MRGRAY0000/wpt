import abc
import inspect
import os
import re
from typing import Any, List, Match, Optional, Pattern, Text, Tuple, cast


Error = Tuple[str, str, str, Optional[int]]

def collapse(text: Text) -> Text:
    return inspect.cleandoc(str(text)).replace("\n", " ")


class Rule(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def name(self) -> Text:
        pass

    @abc.abstractproperty
    def description(self) -> Text:
        pass

    to_fix: Optional[Text] = None

    @classmethod
    def error(cls, path: Text, context: Tuple[Any, ...] = (), line_no: Optional[int] = None) -> Error:
        name = cast(str, cls.name)
        description = cast(str, cls.description) % context
        return (name, description, path, line_no)


class MissingLink(Rule):
    name = "MISSING-LINK"
    description = "Testcase file must have a link to a spec"
    to_fix = """
        Ensure that there is a `<link rel="help" href="[url]">` for the spec.
        `MISSING-LINK` is designed to ensure that the CSS build tool can find
        the tests. Note that the CSS build system is primarily used by
        [test.csswg.org/](http://test.csswg.org/), which doesn't use
        `wptserve`, so `*.any.js` and similar tests won't work there; stick
        with the `.html` equivalent.
    """


class PathLength(Rule):
    name = "PATH LENGTH"
    description = "/%s longer than maximum path length (%d > 150)"
    to_fix = "use shorter filename to rename the test file"


class FileType(Rule):
    name = "FILE TYPE"
    description = "/%s is an unsupported file type (%s)"


class WorkerCollision(Rule):
    name = "WORKER COLLISION"
    description = collapse("""
        path ends with %s which collides with generated tests from %s files
    """)


class GitIgnoreFile(Rule):
    name = "GITIGNORE"
    description = ".gitignore found outside the root"


class MojomJSFile(Rule):
    name = "MOJOM-JS"
    description = "Don't check *.mojom.js files into WPT"
    to_fix = """
        Check if the file is already included in mojojs.zip:
        https://source.chromium.org/chromium/chromium/src/+/master:chrome/tools/build/linux/FILES.cfg
        If yes, use `loadMojoResources` from `resources/test-only-api.js` to load
        it; if not, contact ecosystem-infra@chromium.org for adding new files
        to mojojs.zip.
    """


class AhemCopy(Rule):
    name = "AHEM COPY"
    description = "Don't add extra copies of Ahem, use /fonts/Ahem.ttf"


class AhemSystemFont(Rule):
    name = "AHEM SYSTEM FONT"
    description = "Don't use Ahem as a system font, use /fonts/ahem.css"


# TODO: Add tests for this rule
class IgnoredPath(Rule):
    name = "IGNORED PATH"
    description = collapse("""
        %s matches an ignore filter in .gitignore - please add a .gitignore
        exception
    """)


class ParseFailed(Rule):
    name = "PARSE-FAILED"
    description = "Unable to parse file"
    to_fix = """
        examine the file to find the causes of any parse errors, and fix them.
    """


class ContentManual(Rule):
    name = "CONTENT-MANUAL"
    description = "Manual test whose filename doesn't end in '-manual'"


class ContentVisual(Rule):
    name = "CONTENT-VISUAL"
    description = "Visual test whose filename doesn't end in '-visual'"


class AbsoluteUrlRef(Rule):
    name = "ABSOLUTE-URL-REF"
    description = collapse("""
        Reference test with a reference file specified via an absolute URL:
        '%s'
    """)


class SameFileRef(Rule):
    name = "SAME-FILE-REF"
    description = "Reference test which points at itself as a reference"


class NonexistentRef(Rule):
    name = "NON-EXISTENT-REF"
    description = collapse("""
        Reference test with a non-existent '%s' relationship reference: '%s'
    """)


class MultipleTimeout(Rule):
    name = "MULTIPLE-TIMEOUT"
    description = "More than one meta name='timeout'"
    to_fix = """
        ensure each test file has only one instance of a `<meta
        name="timeout"...>` element
    """


class InvalidTimeout(Rule):
    name = "INVALID-TIMEOUT"
    description = collapse("""
        Test file with `<meta name='timeout'...>` element that has a `content`
        attribute whose value is not `long`: %s
    """)
    to_fix = "replace the value of the `content` attribute with `long`"


class MultipleTestharness(Rule):
    name = "MULTIPLE-TESTHARNESS"
    description = "More than one `<script src='/resources/testharness.js'>`"
    to_fix = """
        Ensure each test has only one `<script
        src='/resources/testharness.js'>` instance.
        For `.js` tests, remove `// META: script=/resources/testharness.js`,
        which wptserve already adds to the boilerplate markup.
    """


class MissingReftestWait(Rule):
    name = "MISSING-REFTESTWAIT"
    description = "Missing `class=reftest-wait`"
    to_fix = """
        ensure tests that include reftest-wait.js also use class=reftest-wait on the root element.
    """


class MissingTestharnessReport(Rule):
    name = "MISSING-TESTHARNESSREPORT"
    description = "Missing `<script src='/resources/testharnessreport.js'>`"
    to_fix = """
        ensure each test file contains `<script
        src='/resources/testharnessreport.js'>`
    """


class MultipleTestharnessReport(Rule):
    name = "MULTIPLE-TESTHARNESSREPORT"
    description = "More than one `<script src='/resources/testharnessreport.js'>`"
    to_fix = """
        Ensure each test has only one `<script
        src='/resources/testharnessreport.js'>` instance.
        For `.js` tests, remove `// META: script=/resources/testharnessreport.js`,
        which wptserve already adds to the boilerplate markup.
    """


class VariantMissing(Rule):
    name = "VARIANT-MISSING"
    description = collapse("""
        Test file with a `<meta name='variant'...>` element that's missing a
        `content` attribute
    """)
    to_fix = """
        add a `content` attribute with an appropriate value to the `<meta
        name='variant'...>` element
    """


class MalformedVariant(Rule):
    name = "MALFORMED-VARIANT"
    description = collapse("""
        %s must be a non empty string
        and start with '?' or '#'
    """)


class LateTimeout(Rule):
    name = "LATE-TIMEOUT"
    description = "`<meta name=timeout>` seen after testharness.js script"
    description = collapse("""
        Test file with `<meta name='timeout'...>` element after `<script
        src='/resources/testharnessreport.js'>` element
    """)
    to_fix = """
        move the `<meta name="timeout"...>` element to precede the `script`
        element.
    """


class EarlyTestharnessReport(Rule):
    name = "EARLY-TESTHARNESSREPORT"
    description = collapse("""
        Test file has an instance of
        `<script src='/resources/testharnessreport.js'>` prior to
        `<script src='/resources/testharness.js'>`
    """)
    to_fix = "flip the order"


class EarlyTestdriverVendor(Rule):
    name = "EARLY-TESTDRIVER-VENDOR"
    description = collapse("""
        Test file has an instance of
        `<script src='/resources/testdriver-vendor.js'>` prior to
        `<script src='/resources/testdriver.js'>`
    """)
    to_fix = "flip the order"


class MultipleTestdriver(Rule):
    name = "MULTIPLE-TESTDRIVER"
    description = "More than one `<script src='/resources/testdriver.js'>`"


class MissingTestdriverVendor(Rule):
    name = "MISSING-TESTDRIVER-VENDOR"
    description = "Missing `<script src='/resources/testdriver-vendor.js'>`"


class MultipleTestdriverVendor(Rule):
    name = "MULTIPLE-TESTDRIVER-VENDOR"
    description = "More than one `<script src='/resources/testdriver-vendor.js'>`"


class TestharnessPath(Rule):
    name = "TESTHARNESS-PATH"
    description = "testharness.js script seen with incorrect path"


class TestharnessReportPath(Rule):
    name = "TESTHARNESSREPORT-PATH"
    description = "testharnessreport.js script seen with incorrect path"


class TestdriverPath(Rule):
    name = "TESTDRIVER-PATH"
    description = "testdriver.js script seen with incorrect path"


class TestdriverUnsupportedQueryParameter(Rule):
    name = "TESTDRIVER-UNSUPPORTED-QUERY-PARAMETER"
    description = "testdriver.js script seen with unsupported query parameters"


class TestdriverVendorPath(Rule):
    name = "TESTDRIVER-VENDOR-PATH"
    description = "testdriver-vendor.js script seen with incorrect path"


class TestdriverInUnsupportedType(Rule):
    name = "TESTDRIVER-IN-UNSUPPORTED-TYPE"
    description = "testdriver.js included in a %s test, which doesn't support testdriver.js"


class OpenNoMode(Rule):
    name = "OPEN-NO-MODE"
    description = "File opened without providing an explicit mode (note: binary files must be read with 'b' in the mode flags)"


class UnknownGlobalMetadata(Rule):
    name = "UNKNOWN-GLOBAL-METADATA"
    description = "Unexpected value for global metadata"


class BrokenGlobalMetadata(Rule):
    name = "BROKEN-GLOBAL-METADATA"
    description = "Invalid global metadata: %s"


class UnknownTimeoutMetadata(Rule):
    name = "UNKNOWN-TIMEOUT-METADATA"
    description = "Unexpected value for timeout metadata"


class UnknownMetadata(Rule):
    name = "UNKNOWN-METADATA"
    description = "Unexpected kind of metadata"


class StrayMetadata(Rule):
    name = "STRAY-METADATA"
    description = "Metadata comments should start the file"


class IndentedMetadata(Rule):
    name = "INDENTED-METADATA"
    description = "Metadata comments should start the line"


class BrokenMetadata(Rule):
    name = "BROKEN-METADATA"
    description = "Metadata comment is not formatted correctly"


class TestharnessInOtherType(Rule):
    name = "TESTHARNESS-IN-OTHER-TYPE"
    description = "testharness.js included in a %s test"


class ReferenceInOtherType(Rule):
    name = "REFERENCE-IN-OTHER-TYPE"
    description = "Reference link included in a %s test"


class DuplicateBasenamePath(Rule):
    name = "DUPLICATE-BASENAME-PATH"
    description = collapse("""
            File has identical basename path (path excluding extension) as
            other file(s) (found extensions: %s)
    """)
    to_fix = "rename files so they have unique basename paths"


class DuplicatePathCaseInsensitive(Rule):
    name = "DUPLICATE-CASE-INSENSITIVE-PATH"
    description = collapse("""
            Path differs from path %s only in case
    """)
    to_fix = "rename files so they are unique irrespective of case"


class TentativeDirectoryName(Rule):
    name = "TENTATIVE-DIRECTORY-NAME"
    description = "Directories for tentative tests must be named exactly 'tentative'"
    to_fix = "rename directory to be called 'tentative'"


class InvalidMetaFile(Rule):
    name = "INVALID-META-FILE"
    description = "The META.yml is not a YAML file with the expected structure"


class InvalidWebFeaturesFile(Rule):
    name = "INVALID-WEB-FEATURES-FILE"
    description = "The WEB_FEATURES.yml file contains an invalid structure"


class MissingTestInWebFeaturesFile(Rule):
    name = "MISSING-WEB-FEATURES-FILE"
    description = collapse("""
        The WEB_FEATURES.yml file references a test that does not exist: '%s'
    """)


EXTENSIONS = {
    "html": [".html", ".htm"],
    "xhtml": [".xht", ".xhtml"],
    "svg": [".svg"],
    "js": [".js", ".mjs"],
    "python": [".py"]
}
EXTENSIONS["markup"] = EXTENSIONS["html"] + EXTENSIONS["xhtml"] + EXTENSIONS["svg"]
EXTENSIONS["js_all"] = EXTENSIONS["markup"] + EXTENSIONS["js"]


class Regexp(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def pattern(self) -> bytes:
        pass

    @abc.abstractproperty
    def name(self) -> Text:
        pass

    @abc.abstractproperty
    def description(self) -> Text:
        pass

    file_extensions: Optional[List[Text]] = None

    def __init__(self) -> None:
        self._re: Pattern[bytes] = re.compile(self.pattern)

    def applies(self, path: Text) -> bool:
        return (self.file_extensions is None or
                os.path.splitext(path)[1] in self.file_extensions)

    def search(self, line: bytes) -> Optional[Match[bytes]]:
        return self._re.search(line)


class TabsRegexp(Regexp):
    pattern = b"^\t"
    name = "INDENT TABS"
    description = "Test-file line starts with one or more tab characters"
    to_fix = "use spaces to replace any tab characters at beginning of lines"


class CRRegexp(Regexp):
    pattern = b"\r$"
    name = "CR AT EOL"
    description = "Test-file line ends with CR (U+000D) character"
    to_fix = """
        reformat file so each line just has LF (U+000A) line ending (standard,
        cross-platform "Unix" line endings instead of, e.g., DOS line endings).
    """


class SetTimeoutRegexp(Regexp):
    pattern = br"setTimeout\s*\("
    name = "SET TIMEOUT"
    file_extensions = EXTENSIONS["js_all"]
    description = "setTimeout used"
    to_fix = """
        replace all `setTimeout(...)` calls with `step_timeout(...)` calls
    """


class W3CTestOrgRegexp(Regexp):
    pattern = br"w3c\-test\.org"
    name = "W3C-TEST.ORG"
    description = "Test-file line has the string `w3c-test.org`"
    to_fix = """
        either replace the `w3c-test.org` string with the expression
        `{{host}}:{{ports[http][0]}}` or a generic hostname like `example.org`
    """


class WebPlatformTestRegexp(Regexp):
    pattern = br"web\-platform\.test"
    name = "WEB-PLATFORM.TEST"
    description = "Internal web-platform.test domain used"
    to_fix = """
        use [server-side substitution](https://web-platform-tests.org/writing-tests/server-pipes.html#sub),
        along with the [`.sub` filename-flag](https://web-platform-tests.org/writing-tests/file-names.html#test-features),
        to replace web-platform.test with `{{domains[]}}`
    """


class Webidl2Regexp(Regexp):
    pattern = br"webidl2\.js"
    name = "WEBIDL2.JS"
    description = "Legacy webidl2.js script used"


class ConsoleRegexp(Regexp):
    pattern = br"console\.[a-zA-Z]+\s*\("
    name = "CONSOLE"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test-file line has a `console.*(...)` call"
    to_fix = """
        remove the `console.*(...)` call (and in some cases, consider adding an
        `assert_*` of some kind in place of it)
    """


class GenerateTestsRegexp(Regexp):
    pattern = br"generate_tests\s*\("
    name = "GENERATE_TESTS"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test file line has a generate_tests call"
    to_fix = "remove the call and call `test()` a number of times instead"


class PrintRegexp(Regexp):
    pattern = br"print(?:\s|\s*\()"
    name = "PRINT STATEMENT"
    file_extensions = EXTENSIONS["python"]
    description = collapse("""
        A server-side python support file contains a `print` statement
    """)
    to_fix = """
        remove the `print` statement or replace it with something else that
        achieves the intended effect (e.g., a logging call)
    """


class LayoutTestsRegexp(Regexp):
    pattern = br"(eventSender|testRunner|internals)\."
    name = "LAYOUTTESTS APIS"
    file_extensions = EXTENSIONS["js_all"]
    description = "eventSender/testRunner/internals used; these are LayoutTests-specific APIs (WebKit/Blink)"


class MissingDepsRegexp(Regexp):
    pattern = br"[^\w]/gen/"
    name = "MISSING DEPENDENCY"
    file_extensions = EXTENSIONS["js_all"]
    description = "Chromium-specific content referenced"
    to_fix = "Reimplement the test to use well-documented testing interfaces"


class SpecialPowersRegexp(Regexp):
    pattern = b"SpecialPowers"
    name = "SPECIALPOWERS API"
    file_extensions = EXTENSIONS["js_all"]
    description = "SpecialPowers used; this is gecko-specific and not supported in wpt"


class TrailingWhitespaceRegexp(Regexp):
    name = "TRAILING WHITESPACE"
    description = "Whitespace at EOL"
    pattern = b"[ \t\f\v]$"
    to_fix = """Remove trailing whitespace from all lines in the file."""


class AssertThrowsRegexp(Regexp):
    pattern = br"[^.]assert_throws\("
    name = "ASSERT_THROWS"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test-file line has an `assert_throws(...)` call"
    to_fix = """Replace with `assert_throws_dom` or `assert_throws_js` or `assert_throws_exactly`"""


class PromiseRejectsRegexp(Regexp):
    pattern = br"promise_rejects\("
    name = "PROMISE_REJECTS"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test-file line has a `promise_rejects(...)` call"
    to_fix = """Replace with promise_rejects_dom or promise_rejects_js or `promise_rejects_exactly`"""


class AssertPreconditionRegexp(Regexp):
    pattern = br"[^.]assert_precondition\("
    name = "ASSERT-PRECONDITION"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test-file line has an `assert_precondition(...)` call"
    to_fix = """Replace with `assert_implements` or `assert_implements_optional`"""


class HTMLInvalidSyntaxRegexp(Regexp):
    pattern = (br"<(a|abbr|article|audio|b|bdi|bdo|blockquote|body|button|canvas|caption|cite|code|colgroup|data|datalist|dd|del|details|"
               br"dfn|dialog|div|dl|dt|em|fieldset|figcaption|figure|footer|form|h[1-6]|head|header|html|i|iframe|ins|kbd|label|legend|li|"
               br"main|map|mark|menu|meter|nav|noscript|object|ol|optgroup|option|output|p|picture|pre|progress|q|rp|rt|ruby|s|samp|script|"
               br"search|section|select|slot|small|span|strong|style|sub|summary|sup|table|tbody|td|template|textarea|tfoot|th|thead|time|"
               br"title|tr|u|ul|var|video)(\s+[^>]+)?\s*/>")
    name = "HTML INVALID SYNTAX"
    file_extensions = EXTENSIONS["html"]
    description = "Test-file line has a non-void HTML tag with /> syntax"
    to_fix = """Replace with start tag and end tag"""


class TestDriverInternalRegexp(Regexp):
    pattern = br"test_driver_internal"
    name = "TEST DRIVER INTERNAL"
    file_extensions = EXTENSIONS["js_all"]
    description = "Test-file uses test_driver_internal API"
    to_fix = """Only use test_driver public API"""
