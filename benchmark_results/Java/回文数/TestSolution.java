import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TestSolution {
    @Test
    void testPositivePalindrome() {
        assertTrue(Solution.is_palindrome(121));
    }

    @Test
    void testNegativePalindrome() {
        assertFalse(Solution.is_palindrome(-121));
    }

    @Test
    void testZeroPalindrome() {
        assertTrue(Solution.is_palindrome(0));
    }

    @Test
    void testSingleDigitPalindrome() {
        assertTrue(Solution.is_palindrome(5));
    }

    @Test
    void testMultiDigitPalindrome() {
        assertTrue(Solution.is_palindrome(12321));
    }

    @Test
    void testMultiDigitNonPalindrome() {
        assertFalse(Solution.is_palindrome(12345));
    }
}