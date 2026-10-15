$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class PortraitProcessor
{
    public static void Process(string srcPath, string destPath, int targetSize)
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

            for (int x = 0; x < w; x++)
            {
                TryEnqueue(x, 0, w, h, bytes, data.Stride, visited, queue);
                TryEnqueue(x, h - 1, w, h, bytes, data.Stride, visited, queue);
            }
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
                bytes[idx + 3] = 0; // Alpha = 0

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

            int boxW = (maxX - minX + 1);
            int boxH = (maxY - minY + 1);
            int boxSize = Math.Max(boxW, boxH);

            int cx_box = minX + boxW / 2;
            int cy_box = minY + boxH / 2;

            int cropX = Math.Max(0, cx_box - boxSize / 2);
            int cropY = Math.Max(0, cy_box - boxSize / 2);
            int cropW = Math.Min(w - cropX, boxSize);
            int cropH = Math.Min(h - cropY, boxSize);

            using (Bitmap squareBmp = new Bitmap(cropW, cropH, PixelFormat.Format32bppArgb))
            {
                using (Graphics cg = Graphics.FromImage(squareBmp))
                {
                    cg.DrawImage(bmp, new Rectangle(0, 0, cropW, cropH), new Rectangle(cropX, cropY, cropW, cropH), GraphicsUnit.Pixel);
                }

                using (Bitmap finalBmp = new Bitmap(targetSize, targetSize, PixelFormat.Format32bppArgb))
                {
                    using (Graphics fg = Graphics.FromImage(finalBmp))
                    {
                        fg.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                        fg.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
                        fg.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
                        fg.DrawImage(squareBmp, 0, 0, targetSize, targetSize);
                    }
                    finalBmp.Save(destPath, ImageFormat.Png);
                    Console.WriteLine("Saved Portrait: " + destPath + " (" + targetSize + "x" + targetSize + ")");
                }
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

        if (r >= 235 && g >= 235 && b >= 235)
        {
            queue.Enqueue(p);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

$src = "C:\Users\Pavilion\.gemini\antigravity-ide\brain\6e833c29-d93e-4d54-9f32-938da0e0debe\portrait_bolu_calico_1791343712025.jpg"
$dest = "assets\portraits\portrait_bolu.png"

[PortraitProcessor]::Process($src, $dest, 256)
Write-Output "SUCCESS PORTRAIT"
