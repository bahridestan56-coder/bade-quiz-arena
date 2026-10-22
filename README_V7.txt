BaDe Quiz Arena v7 - Yönetim Paneli

1. ZIP içindeki dosyaları GitHub v6-test dalının KÖKÜNE yükleyin. main dalını değiştirmeyin.
2. Render test servisinin dağıtımını bekleyin. Öğretmen şifresi ile giriş yapın.
3. "Soru, Konu ve Tasarım Yönetimi" düğmesinden paneli açın.
4. Veritabanı bağlanmamışsa Render Free yeniden dağıtımında panelden kaydedilen veriler kaybolabilir. Soru bankasını JSON olarak yedekleyin.
5. Kalıcı kayıt için bir PostgreSQL veritabanı açın; bağlantı dizesini Render test servisi Environment bölümüne DATABASE_URL adıyla ekleyin. Uygulama bade_store tablosunu kendisi oluşturur. Veritabanı hizmeti bağlantısı için SSL gerekebilir (ör. ?sslmode=require).
6. BADE_ADMIN_PASSWORD ortam değişkenini güçlü ve gizli bir şifreye ayarlayın.
7. Soruları yalnızca yarışma lobisindeyken değiştirin.
8. JSON yükleme mevcut soru bankasının yerine geçer; öncesinde yedek indirin.

Bu bir test sürümüdür; main sürümünüz korunur.
