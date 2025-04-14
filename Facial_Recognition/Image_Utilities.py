import cv2
import numpy as np
import pywt
from scipy.signal import wiener
from skimage.restoration import denoise_wavelet, denoise_nl_means
from skimage.util import img_as_ubyte
from skimage.filters import sobel


# ====================================================
# 1. Tăng độ phân giải (Super-Resolution)
# ====================================================
class SuperResolution:
    @staticmethod
    def bicubic_interpolation(image, scale_factor=2):
        # Ý tưởng: Phương pháp nội suy Bicubic dùng 16 điểm lân cận để tính giá trị mới, 
        # giúp tăng độ phân giải đồng thời giữ được các chi tiết mượt mà.
        h, w = image.shape[:2]
        new_dim = (int(w * scale_factor), int(h * scale_factor))
        return cv2.resize(image, new_dim, interpolation=cv2.INTER_CUBIC)


# ====================================================
# 2. Làm nét ảnh (Image Sharpening)
# ====================================================
class ImageSharpening:
    @staticmethod
    def unsharp_masking(image, kernel_size=(5,5), sigma=1.0, amount=1.5):
        # Ý tưởng: Sử dụng "unsharp masking" để làm nét ảnh, bằng cách trừ đi ảnh làm mờ và kết hợp trở lại.
        blurred = cv2.GaussianBlur(image, kernel_size, sigma)
        return cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)

    @staticmethod
    def high_pass_filtering(image):
        # Ý tưởng: Lọc thông cao bằng kernel có trọng số âm ở xung quanh và dương ở tâm,
        # qua đó nhấn mạnh các biên, kết hợp với ảnh gốc để tạo hiệu ứng làm nét.
        kernel = np.array([[-1, -1, -1],
                           [-1,  8, -1],
                           [-1, -1, -1]])
        high_pass = cv2.filter2D(image, -1, kernel)
        return cv2.addWeighted(image, 1, high_pass, 0.5, 0)

    @staticmethod
    def laplacian_sharpening(image):
        # Ý tưởng: Dùng biến đổi Laplacian để phát hiện biên (đạo hàm bậc hai) và kết hợp với ảnh gốc.
        lap = cv2.Laplacian(image, cv2.CV_64F)
        lap = cv2.convertScaleAbs(lap)
        return cv2.addWeighted(image, 1, lap, 1, 0)

    @staticmethod
    def gradient_based_sharpening(image):
        # Ý tưởng: Tính gradient theo hướng x và y bằng Sobel để phát hiện cạnh, 
        # sau đó kết hợp biên đã tính với ảnh gốc để làm nổi bật các chi tiết.
        sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient = cv2.magnitude(sobelx, sobely)
        gradient = cv2.convertScaleAbs(gradient)
        return cv2.addWeighted(image, 1, gradient, 0.5, 0)

    @staticmethod
    def wiener_deconvolution(image, kernel_size=5):
        # Ý tưởng: Áp dụng giải tích Wiener để khôi phục các chi tiết của ảnh sau khi bị mờ,
        # bằng cách giải bài toán nghịch đảo của phép nhân chập có nhiễu.
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        deconv = wiener(gray, (kernel_size, kernel_size))
        # Giới hạn giá trị pixel trong khoảng [0, 255] và chuyển về kiểu uint8
        return np.clip(deconv, 0, 255).astype(np.uint8)


# ====================================================
# 3. Khử nhiễu ảnh (Image Denoising)
# ====================================================
class ImageDenoising:
    @staticmethod
    def gaussian_filtering(image, sigma=1):
        # Ý tưởng: Lọc Gaussian giúp làm mờ nhiễu theo cách trung bình hóa các giá trị pixel lân cận.
        return cv2.GaussianBlur(image, (0, 0), sigma)

    @staticmethod
    def median_filtering(image, kernel_size=3):
        # Ý tưởng: Lọc trung vị (Median filter) làm giảm nhiễu salt-and-pepper bằng cách thay thế giá trị pixel bằng giá trị trung vị.
        return cv2.medianBlur(image, kernel_size)

    @staticmethod
    def bilateral_filtering(image, diameter=9, sigmaColor=75, sigmaSpace=75):
        # Ý tưởng: Bộ lọc bilateral làm mờ ảnh trong khi vẫn giữ lại các biên, vì thế được sử dụng để giảm nhiễu mà không mất chi tiết.
        return cv2.bilateralFilter(image, diameter, sigmaColor, sigmaSpace)

    @staticmethod
    def non_local_means_denoising(image, h=10, patch_size=7, patch_distance=11):
        # Ý tưởng: Non-local means denoising tìm kiếm các patch tương đồng khắp ảnh để tính trung bình giảm nhiễu hiệu quả.
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        denoised = denoise_nl_means(
            image,
            h=h,
            patch_size=patch_size,
            patch_distance=patch_distance,
            channel_axis=-1
        )
        return img_as_ubyte(denoised)

    @staticmethod
    def wavelet_denoising(image, wavelet='db1', mode='soft', rescale_sigma=True):
        # Ý tưởng: Sử dụng biến đổi wavelet để phân tách các thành phần tần số của ảnh và giảm nhiễu trên các hệ số tương ứng.
        if len(image.shape) == 3:
            channels = cv2.split(image)
            denoised_channels = []
            for ch in channels:
                denoised = denoise_wavelet(ch, wavelet=wavelet, mode=mode, rescale_sigma=rescale_sigma)
                denoised_channels.append(img_as_ubyte(denoised))
            return cv2.merge(denoised_channels)
        else:
            denoised = denoise_wavelet(image, wavelet=wavelet, mode=mode, rescale_sigma=rescale_sigma)
            return img_as_ubyte(denoised)

    @staticmethod
    def anisotropic_diffusion(image, num_iter=10, kappa=50, gamma=0.1):
        # Ý tưởng: Diffusion dị hướng giúp giảm nhiễu bằng cách cập nhật pixel dựa trên các pixel lân cận
        # mà vẫn bảo toàn các biên nhờ vào trọng số điều chỉnh giảm theo hàm số mũ.
        if image.dtype != np.float32:
            image = image.astype(np.float32)
        for _ in range(num_iter):
            deltaN = np.roll(image, -1, axis=0) - image
            deltaS = np.roll(image, 1, axis=0) - image
            deltaE = np.roll(image, -1, axis=1) - image
            deltaW = np.roll(image, 1, axis=1) - image
            cN = np.exp(-(deltaN/kappa)**2)
            cS = np.exp(-(deltaS/kappa)**2)
            cE = np.exp(-(deltaE/kappa)**2)
            cW = np.exp(-(deltaW/kappa)**2)
            image = image + gamma * (cN*deltaN + cS*deltaS + cE*deltaE + cW*deltaW)
        return np.clip(image, 0, 255).astype(np.uint8)


# ====================================================
# 4. Cân bằng sáng và màu sắc (Color & Brightness Adjustment)
# ====================================================
class ColorBrightnessAdjustment:
    @staticmethod
    def gamma_correction(image, gamma=1.0):
        # Ý tưởng: Điều chỉnh độ sáng thông qua biến đổi gamma, cải thiện hoặc giảm bớt mức sáng không đồng đều.
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(image, table)

    @staticmethod
    def histogram_equalization(image):
        # Ý tưởng: Cân bằng histogram nhằm nâng cao độ tương phản của ảnh.
        if len(image.shape) == 2:
            return cv2.equalizeHist(image)
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        # Chỉ cân bằng kênh độ sáng (Y)
        ycrcb[:,:,0] = cv2.equalizeHist(ycrcb[:,:,0])
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    @staticmethod
    def adaptive_histogram_equalization(image, clipLimit=2.0, tileGridSize=(8,8)):
        # Ý tưởng: CLAHE – phiên bản nâng cao của histogram equalization – áp dụng trên từng vùng nhỏ để hạn chế over-enhancement của nhiễu.
        clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize)
        if len(image.shape) == 2:
            return clahe.apply(image)
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        ycrcb[:,:,0] = clahe.apply(ycrcb[:,:,0])
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    @staticmethod
    def retinex_algorithm(image, sigma=30):
        # Ý tưởng: Thuật toán Retinex mô phỏng cách mắt người nhận thức ánh sáng để cải thiện độ tương phản. 
        # Ở đây, ảnh được chuyển về grayscale để tính log hiệu giữa ảnh gốc và ảnh làm mờ.
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = image.astype(np.float32) + 1.0
        blur = cv2.GaussianBlur(image, (0,0), sigma)
        retinex = np.log(image) - np.log(blur + 1)
        retinex = cv2.normalize(retinex, None, 0, 255, cv2.NORM_MINMAX)
        return retinex.astype(np.uint8)

    @staticmethod
    def white_balance_correction(image):
        # Ý tưởng: Hiệu chỉnh cân bằng trắng giúp điều chỉnh sai lệch màu sắc do ánh sáng không đồng đều thông qua chuyển đổi sang không gian LAB.
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        avg_a = np.average(lab[:,:,1])
        avg_b = np.average(lab[:,:,2])
        lab[:,:,1] = lab[:,:,1] - ((avg_a - 128) * (lab[:,:,0] / 255.0) * 1.1)
        lab[:,:,2] = lab[:,:,2] - ((avg_b - 128) * (lab[:,:,0] / 255.0) * 1.1)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


# ====================================================
# 5. Biến đổi hình dạng và cấu trúc ảnh (Geometric & Structural Enhancements)
# ====================================================
class GeometricEnhancements:
    @staticmethod
    def scaling_resampling(image, scale_factor=1.0, interpolation=cv2.INTER_LINEAR):
        # Ý tưởng: Thay đổi kích thước ảnh thông qua nội suy. Có thể dùng cho việc phóng to hoặc thu nhỏ ảnh.
        h, w = image.shape[:2]
        new_dim = (int(w * scale_factor), int(h * scale_factor))
        return cv2.resize(image, new_dim, interpolation=interpolation)

    @staticmethod
    def rotation(image, angle, center=None, scale=1.0):
        # Ý tưởng: Xoay ảnh quanh một tâm nhất định, hữu ích cho việc điều chỉnh góc nhìn.
        h, w = image.shape[:2]
        if center is None:
            center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, scale)
        return cv2.warpAffine(image, M, (w, h))

    @staticmethod
    def perspective_transformation(image, src_points, dst_points):
        # Ý tưởng: Biến đổi phối cảnh giúp hiệu chỉnh hình dạng của ảnh theo các điểm đã cho.
        M = cv2.getPerspectiveTransform(np.float32(src_points), np.float32(dst_points))
        h, w = image.shape[:2]
        return cv2.warpPerspective(image, M, (w, h))

    @staticmethod
    def morphological_operations(image, operation='opening', kernel_size=3, iterations=1):
        # Ý tưởng: Sử dụng các phép biến đổi hình thái (erosion, dilation, opening, closing) để xử lý nhiễu hoặc tạo cấu trúc cho đối tượng trong ảnh.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        if operation == 'erosion':
            return cv2.erode(image, kernel, iterations=iterations)
        elif operation == 'dilation':
            return cv2.dilate(image, kernel, iterations=iterations)
        elif operation == 'opening':
            return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=iterations)
        elif operation == 'closing':
            return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        else:
            raise ValueError("Unsupported morphological operation")


# ====================================================
# 6. Làm mờ ảnh có kiểm soát (Controlled Blurring & Smoothing)
# ====================================================
class ControlledBlurring:
    @staticmethod
    def gaussian_blur(image, sigma=1):
        # Ý tưởng: Làm mờ ảnh sử dụng Gaussian blur để giảm nhiễu mà không làm mất quá nhiều chi tiết.
        return cv2.GaussianBlur(image, (0, 0), sigma)

    @staticmethod
    def motion_blur_simulation(image, kernel_size=15, angle=0):
        # Ý tưởng: Giả lập hiệu ứng làm mờ do chuyển động bằng cách tạo kernel mô phỏng quỹ đạo di chuyển theo góc nhất định.
        M = np.zeros((kernel_size, kernel_size))
        center = kernel_size // 2
        angle_rad = np.deg2rad(angle)
        cos_val = np.cos(angle_rad)
        sin_val = np.sin(angle_rad)
        for i in range(kernel_size):
            x = int(center + (i - center) * cos_val)
            y = int(center + (i - center) * sin_val)
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                M[y, x] = 1
        M = M / np.sum(M)
        return cv2.filter2D(image, -1, M)

    @staticmethod
    def radial_zoom_blur(image, strength=0.5):
        # Ý tưởng: Tạo hiệu ứng mờ khi zoom xoay quanh tâm ảnh, bằng cách cộng dồn nhiều phiên bản ảnh thay đổi kích thước.
        h, w = image.shape[:2]
        blurred = np.zeros_like(image, dtype=np.float32)
        steps = 10
        for i in range(steps):
            scale = 1 + strength * (i / steps)
            resized = cv2.resize(image, (int(w/scale), int(h/scale)))
            resized = cv2.resize(resized, (w, h))
            blurred = blurred + resized.astype(np.float32)
        blurred /= steps
        return blurred.astype(np.uint8)

    @staticmethod
    def surface_blur(image, sigma_space=10, sigma_r=0.15):
        # Ý tưởng: Làm mờ bề mặt với bảo toàn biên sử dụng bộ lọc edge-preserving, giảm nhiễu mà vẫn giữ lại các cạnh rõ nét.
        return cv2.edgePreservingFilter(image, flags=1, sigma_s=sigma_space, sigma_r=sigma_r)


# ====================================================
# 7. Tăng cường cạnh và phát hiện biên (Edge & Contrast Enhancements)
# ====================================================
class EdgeEnhancement:
    @staticmethod
    def edge_detection(image, method='canny'):
        # Ý tưởng: Phát hiện các biên của ảnh sử dụng các phương pháp như Sobel, Prewitt và Canny.
        if method == 'sobel':
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            grad = cv2.Sobel(gray, cv2.CV_64F, 1, 1, ksize=3)
            return cv2.convertScaleAbs(grad)
        elif method == 'prewitt':
            kernelx = np.array([[1, 0, -1],
                                [1, 0, -1],
                                [1, 0, -1]])
            kernely = np.array([[1, 1, 1],
                                [0, 0, 0],
                                [-1, -1, -1]])
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            grad_x = cv2.filter2D(gray, -1, kernelx)
            grad_y = cv2.filter2D(gray, -1, kernely)
            gradient = cv2.addWeighted(np.abs(grad_x), 0.5, np.abs(grad_y), 0.5, 0)
            return gradient
        elif method == 'canny':
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return cv2.Canny(gray, 100, 200)
        else:
            raise ValueError("Phương pháp edge detection không được hỗ trợ")

    @staticmethod
    def gradient_domain_processing(image):
        # Ý tưởng: Kết hợp thông tin gradient với ảnh gốc để làm nổi bật các cạnh mà không làm mất màu sắc tự nhiên.
        if len(image.shape) == 2 or image.shape[2] != 3:
            image_color = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            image_color = image

        gray = cv2.cvtColor(image_color, cv2.COLOR_BGR2GRAY)
        grad = sobel(gray)
        grad = cv2.normalize(grad, None, 0, 255, cv2.NORM_MINMAX)
        grad_color = cv2.cvtColor(grad.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(image_color, 0.8, grad_color, 0.2, 0)


# ====================================================
# 8. Xử lý ảnh trong miền tần số (Frequency Domain Processing)
# ====================================================
class FrequencyDomainProcessing:
    @staticmethod
    def fourier_transform_processing(image):
        # Ý tưởng: Chuyển ảnh sang miền tần số thông qua Fourier Transform để phân tích cấu trúc tần số.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        spectrum = 20 * np.log(np.abs(fshift) + 1)
        spectrum = cv2.normalize(spectrum, None, 0, 255, cv2.NORM_MINMAX)
        return spectrum.astype(np.uint8)

    @staticmethod
    def high_low_pass_filtering(image, filter_type='high', cutoff=30):
        # Ý tưởng: Áp dụng bộ lọc thông cao hoặc thông thấp trên miền Fourier để loại bỏ tần số không mong muốn.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        mask = np.zeros_like(gray, dtype=np.uint8)
        if filter_type == 'low':
            cv2.circle(mask, (ccol, crow), cutoff, 1, thickness=-1)
        elif filter_type == 'high':
            mask.fill(1)
            cv2.circle(mask, (ccol, crow), cutoff, 0, thickness=-1)
        else:
            raise ValueError("filter_type phải là 'high' hoặc 'low'")
        fshift_filtered = fshift * mask
        f_ishift = np.fft.ifftshift(fshift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        img_back = np.abs(img_back)
        img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX)
        return img_back.astype(np.uint8)

    @staticmethod
    def wavelet_transform(image, wavelet='db1', level=1):
        # Ý tưởng: Phân tách ảnh thành các hệ số wavelet nhằm phân tích các thành phần ở nhiều mức tần số.
        coeffs = pywt.wavedec2(image, wavelet=wavelet, level=level)
        return coeffs


# ====================================================
# 9. Cải thiện nhận diện khuôn mặt trên ảnh chất lượng thấp
# ====================================================
class FaceRecognitionEnhancement:
    @staticmethod
    def log_transformation(image, c=1):
        # Ý tưởng: Sử dụng biến đổi logarit để tăng cường chi tiết ở vùng tối, hỗ trợ nhận diện khuôn mặt.
        image_float = image.astype(np.float32)
        log_image = c * np.log1p(image_float)
        log_image = cv2.normalize(log_image, None, 0, 255, cv2.NORM_MINMAX)
        return log_image.astype(np.uint8)

    @staticmethod
    def power_law_transformation(image, c=1, gamma=1.0):
        # Ý tưởng: Áp dụng biến đổi lũy thừa (gamma correction) để điều chỉnh độ tương phản và mức sáng của ảnh.
        image_float = image.astype(np.float32)
        power_image = c * np.power(image_float, gamma)
        power_image = cv2.normalize(power_image, None, 0, 255, cv2.NORM_MINMAX)
        return power_image.astype(np.uint8)

    @staticmethod
    def contrast_stretching(image):
        # Ý tưởng: Kéo giãn biên độ của ảnh dựa trên percentiles để tăng độ tương phản.
        in_min = np.percentile(image, 2)
        in_max = np.percentile(image, 98)
        stretched = (image - in_min) * (255 / (in_max - in_min))
        stretched = np.clip(stretched, 0, 255)
        return stretched.astype(np.uint8)

    @staticmethod
    def color_space_conversion(image, conversion='YCrCb'):
        # Ý tưởng: Chuyển đổi ảnh từ không gian màu BGR sang một không gian khác như YCrCb, HSV hoặc Lab,
        # nhằm tăng cường hiệu suất của các thuật toán nhận diện.
        if conversion == 'YCrCb':
            return cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        elif conversion == 'HSV':
            return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        elif conversion == 'Lab':
            return cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
        else:
            raise ValueError("Conversion không được hỗ trợ")

    @staticmethod
    def edge_aware_filtering(image):
        # Ý tưởng: Áp dụng bộ lọc bilateral để giảm nhiễu mà vẫn giữ lại các cạnh quan trọng,
        # hỗ trợ cải thiện quá trình nhận diện khuôn mặt.
        return cv2.bilateralFilter(image, 9, 75, 75)


# ====================================================
# 10. Hiệu chỉnh biến dạng do camera chất lượng thấp
# ====================================================
class DistortionCorrection:
    @staticmethod
    def radial_distortion_correction(image, camera_matrix, dist_coeffs):
        # Ý tưởng: Sử dụng thông tin của ma trận camera và hệ số méo để hiệu chỉnh biến dạng (như méo cong) của ảnh.
        h, w = image.shape[:2]
        new_cam_mtx, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))
        return cv2.undistort(image, camera_matrix, dist_coeffs, None, new_cam_mtx)

    @staticmethod
    def high_boost_filtering(image, kernel_size=(3,3), boost=1.5):
        # Ý tưởng: Kết hợp làm mờ và tăng cường thành phần tần số cao (high-frequency) nhằm làm nổi bật chi tiết.
        blurred = cv2.GaussianBlur(image, kernel_size, 0)
        high_freq = cv2.subtract(image, blurred)
        high_boost = cv2.addWeighted(image, 1, high_freq, boost, 0)
        return high_boost

# ====================================================
# Video Stabilization (Ổn định video)
# ====================================================
class VideoStabilization:
    def __init__(self):
        self.prev_gray = None

    def stabilize_frame(self, frame):
        # Ý tưởng: Giảm thiểu rung lắc trong video bằng cách tìm chuyển động giữa các khung hình liên tiếp và áp dụng biến đổi affine.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.prev_gray is None:
            self.prev_gray = gray
            return frame

        # Khởi tạo ma trận biến đổi affine ban đầu
        warp_matrix = np.eye(2, 3, dtype=np.float32)

        # Tiêu chí dừng cho thuật toán findTransformECC
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)

        try:
            cc, warp_matrix = cv2.findTransformECC(self.prev_gray, gray, warp_matrix, cv2.MOTION_EUCLIDEAN, criteria)
        except cv2.error as e:
            print("findTransformECC error:", e)

        # Áp dụng biến đổi affine theo ma trận đã tính
        stabilized_frame = cv2.warpAffine(frame, warp_matrix, (frame.shape[1], frame.shape[0]),
                                          flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)

        self.prev_gray = gray

        return stabilized_frame