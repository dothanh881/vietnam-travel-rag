'use client';

import Link from 'next/link';
import { MapPin, MessageCircle, Users, Compass, Star, ChevronRight, Menu, X } from 'lucide-react';
import { useState, useEffect } from 'react';

const destinations = [
  {
    id: 1, name: 'Vịnh Hạ Long', region: 'Quảng Ninh',
    description: 'Di sản thế giới UNESCO nổi tiếng những hòn đảo đá vôi kỳ vĩ.',
    image: 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=600&h=400&fit=crop', rating: 4.9,
  },
  {
    id: 2, name: 'Phố Cổ Hội An', region: 'Quảng Nam',
    description: 'Thành phố cổ với đèn lồng truyền thống lung linh về đêm.',
    image: 'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=600&h=400&fit=crop', rating: 4.8,
  },
  {
    id: 3, name: 'Sa Pa', region: 'Lào Cai',
    description: 'Ruộng bậc thang tuyệt đẹp và văn hóa đồng bào dân tộc phong phú.',
    image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=400&fit=crop', rating: 4.7,
  },
  {
    id: 4, name: 'Phú Quốc', region: 'Kiên Giang',
    description: 'Hòn đảo ngọc với bãi biển trắng và nước biển xanh trong.',
    image: 'https://images.unsplash.com/photo-1589394815804-964ed0be2eb5?w=600&h=400&fit=crop', rating: 4.8,
  },
  {
    id: 5, name: 'Đà Lạt', region: 'Lâm Đồng',
    description: 'Thành phố ngàn hoa với khí hậu mát mẻ quanh năm.',
    image: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=400&fit=crop', rating: 4.7,
  },
  {
    id: 6, name: 'Nha Trang', region: 'Khánh Hòa',
    description: 'Thành phố biển sầm uất với những bãi cát trắng và lặn san hô.',
    image: 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=600&h=400&fit=crop', rating: 4.6,
  },
];

const features = [
  { icon: MapPin, title: '30+ Địa Điểm', desc: 'Dữ liệu đầy đủ về các điểm đến nổi tiếng khắp Việt Nam từ Bắc vào Nam.' },
  { icon: MessageCircle, title: 'AI Thông Minh', desc: 'Trợ lý RAG hiểu ngữ cảnh, trả lời chính xác dựa trên dữ liệu thực tế.' },
  { icon: Compass, title: 'Lịch Trình AI', desc: 'Gợi ý lộ trình cá nhân hóa phù hợp với sở thích và ngân sách của bạn.' },
  { icon: Users, title: 'Hỗ Trợ 24/7', desc: 'Luôn sẵn sàng trả lời mọi thắc mắc về du lịch bất kỳ lúc nào.' },
];

export default function LandingPage() {
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-white text-gray-900 font-sans">

      {/* ── Navbar ── */}
      <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'bg-white/95 backdrop-blur-md shadow-sm border-b border-gray-100' : 'bg-white/80 backdrop-blur-sm'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md">
              <MapPin className="w-4 h-4 text-white" />
            </div>
            <span className="bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">ViVu</span>
          </Link>

          <div className="hidden md:flex items-center gap-7">
            <a href="#destinations" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition">Địa điểm</a>
            <a href="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition">Tính năng</a>
            <a href="#contact" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition">Liên hệ</a>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <Link href="/chat" className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50 text-gray-600 hover:text-emerald-700 transition-all font-medium">
              <MessageCircle className="w-3.5 h-3.5" /> Chat AI
            </Link>
          </div>

          <button className="md:hidden p-2 rounded-lg hover:bg-gray-100" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden bg-white border-t border-gray-100 px-4 py-4 space-y-2 shadow-lg">
            <a href="#destinations" onClick={() => setMenuOpen(false)} className="block text-gray-600 hover:text-gray-900 py-2 text-sm">Địa điểm</a>
            <a href="#features" onClick={() => setMenuOpen(false)} className="block text-gray-600 hover:text-gray-900 py-2 text-sm">Tính năng</a>
            <div className="pt-2 flex flex-col gap-2 border-t border-gray-100 mt-2">
              <Link href="/chat" onClick={() => setMenuOpen(false)} className="w-full py-2 rounded-lg border border-gray-200 text-sm text-center text-gray-700">Chat AI</Link>
            </div>
          </div>
        )}
      </nav>

      {/* ── Hero ── */}
      <section className="pt-16 min-h-screen bg-gradient-to-br from-white via-emerald-50/40 to-teal-50/60 flex items-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-16">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

            {/* Left — text */}
            <div>


              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-gray-900 mb-5">
                Khám Phá{' '}
                <span className="bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent">
                  Việt Nam
                </span>
                <br />
                Cùng Trí Tuệ AI
              </h1>

              <p className="text-lg text-gray-500 leading-relaxed mb-8 max-w-lg">
                Hỏi bất kỳ điều gì về du lịch Việt Nam — địa điểm, lịch trình, ẩm thực, văn hóa. ViVu trả lời chính xác dựa trên dữ liệu thực tế.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 mb-10">
                <Link href="/chat" className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-base transition-all shadow-lg shadow-emerald-200 hover:shadow-emerald-300 hover:-translate-y-0.5">
                  <MessageCircle className="w-5 h-5" /> Bắt đầu hỏi miễn phí
                </Link>
              </div>

              {/* Stats row */}
              <div className="flex items-center gap-8">
                {[['30+', 'Địa điểm'], ['10K+', 'Câu hỏi/ngày'], ['4.9★', 'Đánh giá']].map(([num, label]) => (
                  <div key={label} className="text-center">
                    <div className="text-xl font-bold text-emerald-600">{num}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — banner image */}
            <div className="relative">
              {/* Main image */}
              <div className="relative rounded-3xl overflow-hidden shadow-2xl shadow-emerald-100 border border-white">
                <img
                  src="https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&h=600&fit=crop"
                  alt="Vịnh Hạ Long, Việt Nam"
                  className="w-full h-[420px] lg:h-[500px] object-cover"
                />
                {/* Overlay gradient */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent" />
                {/* Caption chip */}
                <div className="absolute bottom-5 left-5 bg-white/90 backdrop-blur-sm rounded-xl px-4 py-2.5 shadow-lg">
                  <p className="font-semibold text-gray-900 text-sm"> Vịnh Hạ Long</p>
                </div>
              </div>


              {/* Floating card 2 — bottom right */}
              <div className="absolute -bottom-4 -right-4 lg:-right-8 bg-white rounded-2xl shadow-xl border border-gray-100 p-4 hidden md:flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                  <MessageCircle className="w-4 h-4 text-emerald-600" />
                </div>

              </div>

              {/* Decorative circles */}
              <div className="absolute -bottom-8 -left-8 w-40 h-40 bg-emerald-100 rounded-full -z-10 opacity-60" />
              <div className="absolute -top-8 left-1/3 w-20 h-20 bg-teal-100 rounded-full -z-10 opacity-50" />
            </div>
          </div>
        </div>
      </section>

      {/* ── Destinations ── */}
      <section id="destinations" className="py-24 px-4 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">Điểm Đến Nổi Bật</h2>
            <p className="text-gray-500">Hỏi ViVu về bất kỳ địa điểm nào dưới đây</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {destinations.map(dest => (
              <Link href={`/chat?q=${encodeURIComponent('Hãy giới thiệu về ' + dest.name)}`} key={dest.id}
                className="group bg-white rounded-2xl border border-gray-100 overflow-hidden hover:border-emerald-200 hover:-translate-y-1.5 transition-all duration-300 hover:shadow-xl hover:shadow-emerald-50 shadow-sm">
                <div className="relative h-52 overflow-hidden">
                  <img src={dest.image} alt={dest.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                  <span className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm text-gray-700 text-xs px-2.5 py-1 rounded-full font-medium">
                    {dest.region}
                  </span>
                  <div className="absolute bottom-3 left-3 flex items-center gap-1 text-amber-400 text-xs bg-black/30 backdrop-blur-sm px-2 py-1 rounded-full">
                    <Star className="w-3 h-3 fill-amber-400" /> {dest.rating}
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-base text-gray-900 mb-1.5 group-hover:text-emerald-600 transition-colors">{dest.name}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{dest.description}</p>
                  <span className="inline-flex items-center gap-1 mt-3 text-xs text-emerald-600 font-medium group-hover:gap-2 transition-all">
                    Hỏi ViVu <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-24 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">Tại Sao Chọn ViVu?</h2>
            <p className="text-gray-500">Được xây dựng trên công nghệ RAG tiên tiến</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map(f => (
              <div key={f.title} className="bg-white rounded-2xl border border-gray-100 p-6 hover:border-emerald-200 hover:shadow-lg hover:shadow-emerald-50 transition-all hover:-translate-y-0.5 shadow-sm">
                <div className="w-11 h-11 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-emerald-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-white rounded-3xl p-12 border border-gray-100 shadow-lg relative overflow-hidden">
            {/* Subtle accent line top */}
            <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-emerald-400 to-teal-400 rounded-t-3xl" />
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Sẵn Sàng Khám Phá?</h2>
            <p className="text-gray-500 mb-8 text-base font-medium">Bắt đầu trò chuyện với ViVu — không cần đăng ký</p>
            <Link href="/chat" className="inline-flex items-center gap-2 px-10 py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-base transition-all shadow-md shadow-emerald-200 hover:-translate-y-0.5">
              <MessageCircle className="w-5 h-5" /> Bắt đầu ngay →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Contact ── */}
      <section id="contact" className="py-24 px-4 bg-gray-50">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Liên Hệ</h2>
            <p className="text-gray-500">Góp ý hoặc cần hỗ trợ? Chúng tôi luôn lắng nghe</p>
          </div>
          <form className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 space-y-4" onSubmit={e => e.preventDefault()}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input type="text" placeholder="Họ tên" className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition placeholder:text-gray-400" />
              <input type="email" placeholder="Email" className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition placeholder:text-gray-400" />
            </div>
            <textarea placeholder="Nội dung..." rows={5} className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 resize-none transition placeholder:text-gray-400" />
            <button type="submit" className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm transition-all shadow-md shadow-emerald-200">
              Gửi tin nhắn
            </button>
          </form>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-gray-50 border-t border-gray-100 py-14 px-4">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 font-bold text-lg mb-3 text-gray-900">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-sm">
                <MapPin className="w-3.5 h-3.5 text-white" />
              </div>
              ViVu
            </div>
            <p className="text-gray-500 text-sm leading-relaxed font-medium">Trợ lý du lịch AI cho Việt Nam</p>
          </div>
          {[
            { title: 'Sản phẩm', links: [['Chat AI', '/chat'], ['Địa điểm', '#destinations'], ['Tính năng', '#features']] },
            { title: 'Tài khoản', links: [['Đăng nhập', '#'], ['Đăng ký', '#'], ['Hồ sơ', '#']] },
            { title: 'Pháp lý', links: [['Điều khoản', '#'], ['Bảo mật', '#'], ['FAQ', '#']] },
          ].map(col => (
            <div key={col.title}>
              <h4 className="font-bold text-sm mb-4 text-gray-800">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.links.map(([label, href]) => (
                  <li key={label}><Link href={href as string} className="text-gray-500 text-sm font-medium hover:text-emerald-600 transition">{label}</Link></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="max-w-7xl mx-auto border-t border-gray-200 pt-8 flex flex-col sm:flex-row justify-between items-center gap-2">
          <p className="text-gray-500 text-sm font-medium text-center">© 2025 ViVu. Bảo lưu mọi quyền.</p>
        </div>
      </footer>
    </main>
  );
}
