# OpenCV headless dependency shim

RapidOCR declares a dependency on `opencv-python`, whose Linux wheel includes GUI
libraries that are unnecessary in this API. This empty local distribution satisfies
that package requirement and depends on the API-compatible
`opencv-python-headless` distribution instead. It keeps the Vercel function below
the platform's deployment-size limit and avoids runtime dependencies on X11.
