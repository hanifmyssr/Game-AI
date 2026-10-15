$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class BattleSpriteProcessor
{
    public static void Process(string srcPath, string destPath, int pad)
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

            // Enqueue tepi atas dan bawah
            for (int x = 0; x < w; x++)
            {
                TryEnqueue(x, 0, w, h, bytes, data.Stride, visited, queue);
                TryEnqueue(x, h - 1, w, h, bytes, data.Stride, visited, queue);
            }
            // Enqueue tepi kiri dan kanan
            for (int y = 0; y < h; y++)
            {
                TryEnqueue(0, y, w, h, bytes, data.Stride, visited, queue);
                TryEnqueue(w - 1, y, w, h, bytes, data.Stride, visited, queue);
            }

            int[] dx = { 0, 0, 1, -1 };
            int[] dy = { 1, -1, 0, 0 };

            while (queue.Count > 0)
            {
                int curr = queue.Dequeue();
                int cx = curr % w;
                int cy = curr / w;

                int idx = cy * data.Stride + cx * 4;
                bytes[idx + 3] = 0; // Alpha = 0 (Transparent)

                for (int i = 0; i < 4; i++)
                {
                    int nx = cx + dx[i];
                    int ny = cy + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h)
                    {
                        TryEnqueue(nx, ny, w, h, bytes, data.Stride, visited, queue);
                    }
                }
            }

            // Cari bounding box karakter (alpha > 10)
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
                    Console.WriteLine("Cropped & Saved: " + destPath + " (" + cropW + "x" + cropH + ")");
                }
            }
            else
            {
                bmp.Save(destPath, ImageFormat.Png);
                Console.WriteLine("Saved without crop: " + destPath);
            }

            bmp.Dispose();
        }
    }

    private static void TryEnqueue(int x, int y, int w, int h, byte[] bytes, int stride, bool[] visited, Queue<int> queue)
    {
        int p = y * w + x;
        if (visited[p]) return;
        visited[p] = true;

        int idx = y * stride + x * 4;
        byte b = bytes[idx];
        byte g = bytes[idx + 1];
        byte r = bytes[idx + 2];

        // Latar putih atau off-white
        if (r >= 235 && g >= 235 && b >= 235)
        {
            queue.Enqueue(p);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

$src = "C:\Users\Pavilion\.gemini\antigravity-ide\brain\6e833c29-d93e-4d54-9f32-938da0e0debe\battle_bolu_calico_1791343563658.jpg"
$dest = "assets\battle_sprites\battle_bolu.png"

[BattleSpriteProcessor]::Process($src, $dest, 8)
Write-Output "SUCCESS"
