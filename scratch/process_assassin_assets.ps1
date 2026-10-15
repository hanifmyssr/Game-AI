$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class AssassinAssetProcessor
{
    public static void ProcessPortrait(string srcPath, string destPath, int targetSize, int threshold)
    {
        using (Bitmap raw = new Bitmap(srcPath))
        {
            Bitmap resized = new Bitmap(targetSize, targetSize, PixelFormat.Format32bppArgb);
            using (Graphics g = Graphics.FromImage(resized))
            {
                g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
                g.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
                g.DrawImage(raw, 0, 0, targetSize, targetSize);
            }

            int w = resized.Width;
            int h = resized.Height;
            BitmapData data = resized.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int byteCount = data.Stride * h;
            byte[] bytes = new byte[byteCount];
            Marshal.Copy(data.Scan0, bytes, 0, byteCount);

            bool[] visited = new bool[w * h];
            Queue<int> queue = new Queue<int>();

            // Enqueue tepi luar (latar hitam: r, g, b <= threshold)
            for (int x = 0; x < w; x++)
            {
                TryEnqueueBlack(x, 0, w, h, bytes, data.Stride, threshold, visited, queue);
                TryEnqueueBlack(x, h - 1, w, h, bytes, data.Stride, threshold, visited, queue);
            }
            for (int y = 0; y < h; y++)
            {
                TryEnqueueBlack(0, y, w, h, bytes, data.Stride, threshold, visited, queue);
                TryEnqueueBlack(w - 1, y, w, h, bytes, data.Stride, threshold, visited, queue);
            }

            int[] dx = { 0, 0, 1, -1 };
            int[] dy = { 1, -1, 0, 0 };

            while (queue.Count > 0)
            {
                int curr = queue.Dequeue();
                int cx = curr % w;
                int cy = curr / w;

                int idx = cy * data.Stride + cx * 4;
                bytes[idx + 3] = 0; // Alpha = 0

                for (int i = 0; i < 4; i++)
                {
                    int nx = cx + dx[i];
                    int ny = cy + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h)
                    {
                        TryEnqueueBlack(nx, ny, w, h, bytes, data.Stride, threshold, visited, queue);
                    }
                }
            }

            Marshal.Copy(bytes, 0, data.Scan0, byteCount);
            resized.UnlockBits(data);
            resized.Save(destPath, ImageFormat.Png);
            Console.WriteLine("Saved Portrait: " + destPath + " (" + targetSize + "x" + targetSize + ")");
            resized.Dispose();
        }
    }

    private static void TryEnqueueBlack(int x, int y, int w, int h, byte[] bytes, int stride, int threshold, bool[] visited, Queue<int> queue)
    {
        int p = y * w + x;
        if (visited[p]) return;
        visited[p] = true;

        int idx = y * stride + x * 4;
        byte b = bytes[idx];
        byte g = bytes[idx + 1];
        byte r = bytes[idx + 2];

        if (r <= threshold && g <= threshold && b <= threshold)
        {
            queue.Enqueue(p);
        }
    }

    public static void ProcessBattleSprite(string srcPath, string destPath, int pad)
    {
        using (Bitmap raw = new Bitmap(srcPath))
        {
            int w = raw.Width;
            int h = raw.Height;

            Bitmap bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.DrawImage(raw, 0, 0, w, h);
            }

            BitmapData data = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int byteCount = data.Stride * h;
            byte[] bytes = new byte[byteCount];
            Marshal.Copy(data.Scan0, bytes, 0, byteCount);

            bool[] visited = new bool[w * h];
            Queue<int> queue = new Queue<int>();

            // Enqueue tepi luar (latar putih: r, g, b >= 230)
            for (int x = 0; x < w; x++)
            {
                TryEnqueueWhite(x, 0, w, h, bytes, data.Stride, visited, queue);
                TryEnqueueWhite(x, h - 1, w, h, bytes, data.Stride, visited, queue);
            }
            for (int y = 0; y < h; y++)
            {
                TryEnqueueWhite(0, y, w, h, bytes, data.Stride, visited, queue);
                TryEnqueueWhite(w - 1, y, w, h, bytes, data.Stride, visited, queue);
            }

            int[] dx = { 0, 0, 1, -1 };
            int[] dy = { 1, -1, 0, 0 };

            while (queue.Count > 0)
            {
                int curr = queue.Dequeue();
                int cx = curr % w;
                int cy = curr / w;

                int idx = cy * data.Stride + cx * 4;
                bytes[idx + 3] = 0; // Alpha = 0

                for (int i = 0; i < 4; i++)
                {
                    int nx = cx + dx[i];
                    int ny = cy + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h)
                    {
                        TryEnqueueWhite(nx, ny, w, h, bytes, data.Stride, visited, queue);
                    }
                }
            }

            // Cari bounding box
            int minX = w, minY = h, maxX = 0, maxY = 0;
            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    int idx = y * data.Stride + x * 4;
                    if (bytes[idx + 3] > 10)
                    {
                        if (x < minX) minX = x;
                        if (y < minY) minY = y;
                        if (x > maxX) maxX = x;
                        if (y > maxY) maxY = y;
                    }
                }
            }

            Marshal.Copy(bytes, 0, data.Scan0, byteCount);
            bmp.UnlockBits(data);

            if (maxX >= minX && maxY >= minY)
            {
                int cropX = Math.Max(0, minX - pad);
                int cropY = Math.Max(0, minY - pad);
                int cropW = Math.Min(w - cropX, (maxX - minX + 1) + pad * 2);
                int cropH = Math.Min(h - cropY, (maxY - minY + 1) + pad * 2);

                using (Bitmap cropped = new Bitmap(cropW, cropH, PixelFormat.Format32bppArgb))
                {
                    using (Graphics cg = Graphics.FromImage(cropped))
                    {
                        cg.DrawImage(bmp, new Rectangle(0, 0, cropW, cropH), new Rectangle(cropX, cropY, cropW, cropH), GraphicsUnit.Pixel);
                    }
                    cropped.Save(destPath, ImageFormat.Png);
                    Console.WriteLine("Cropped & Saved Battle Sprite: " + destPath + " (" + cropW + "x" + cropH + ")");
                }
            }
            else
            {
                bmp.Save(destPath, ImageFormat.Png);
                Console.WriteLine("Saved Battle Sprite: " + destPath);
            }

            bmp.Dispose();
        }
    }

    private static void TryEnqueueWhite(int x, int y, int w, int h, byte[] bytes, int stride, bool[] visited, Queue<int> queue)
    {
        int p = y * w + x;
        if (visited[p]) return;
        visited[p] = true;

        int idx = y * stride + x * 4;
        byte b = bytes[idx];
        byte g = bytes[idx + 1];
        byte r = bytes[idx + 2];

        if (r >= 230 && g >= 230 && b >= 230)
        {
            queue.Enqueue(p);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

$brainDir = "C:\Users\Pavilion\.gemini\antigravity-ide\brain\409736b6-c332-4fc5-89da-c9350a33efdd"
$portraitSrc = "$brainDir\portrait_assassin_1791354445592.jpg"
$battleSrc = "$brainDir\battle_assassin_1791354464051.jpg"

$portraitDst = "assets\portraits\portrait_assassin.png"
$battleDst = "assets\battle_sprites\battle_assassin.png"

[AssassinAssetProcessor]::ProcessPortrait($portraitSrc, $portraitDst, 256, 35)
[AssassinAssetProcessor]::ProcessBattleSprite($battleSrc, $battleDst, 8)
Write-Output "ALL ASSASSIN ASSETS PROCESSED SUCCESSFULLY!"
