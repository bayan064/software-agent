import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TestSolution {
    @Test
    void testCase1() {
        Solution solution = new Solution();
        int[] result = solution.twoSum(new int[]{2, 7, 11, 15}, 9);
        assertArrayEquals(new int[]{0, 1}, result);
    }

    @Test
    void testCase2() {
        Solution solution = new Solution();
        int[] result = solution.twoSum(new int[]{3, 2, 4}, 6);
        assertArrayEquals(new int[]{1, 2}, result);
    }

    @Test
    void testCase3() {
        Solution solution = new Solution();
        int[] result = solution.twoSum(new int[]{3, 3}, 6);
        assertArrayEquals(new int[]{0, 1}, result);
    }

    @Test
    void testCase4() {
        Solution solution = new Solution();
        assertThrows(IllegalArgumentException.class, () -> {
            solution.twoSum(new int[]{1, 2, 3}, 7);
        });
    }
}