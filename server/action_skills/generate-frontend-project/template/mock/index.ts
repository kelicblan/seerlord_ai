import type { MockMethod } from 'vite-plugin-mock'

export default [
  {
    url: '/api/auth/login',
    method: 'post',
    statusCode: 200,
    response: () => {
      return {
        code: 200,
        message: 'success',
        data: {
          token: 'mock-token-' + Date.now(),
          userName: 'admin',
        },
      }
    },
  },
  {
    url: '/api/examples/list',
    method: 'get',
    timeout: 500,
    response: ({ query }: { query: { page?: number; pageSize?: number; keyword?: string; status?: number } }) => {
      const page = Number(query?.page) || 1
      const pageSize = Number(query?.pageSize) || 10
      const allData = [
        { id: 1, title: '示例文章标题一', category: '技术', status: 1, views: 1234, createTime: '2024-01-15 10:30:00' },
        { id: 2, title: '示例文章标题二', category: '产品', status: 1, views: 856, createTime: '2024-01-14 14:20:00' },
        { id: 3, title: '示例文章标题三', category: '运营', status: 0, views: 423, createTime: '2024-01-13 09:15:00' },
        { id: 4, title: '示例文章标题四', category: '设计', status: 1, views: 2156, createTime: '2024-01-12 16:45:00' },
        { id: 5, title: '示例文章标题五', category: '市场', status: 1, views: 789, createTime: '2024-01-11 11:30:00' },
        { id: 6, title: 'Vue3 核心原理深入解析', category: '技术', status: 1, views: 3456, createTime: '2024-01-10 08:00:00' },
        { id: 7, title: 'TypeScript 最佳实践指南', category: '技术', status: 1, views: 2876, createTime: '2024-01-09 15:30:00' },
        { id: 8, title: '产品经理如何写好需求文档', category: '产品', status: 1, views: 1567, createTime: '2024-01-08 11:20:00' },
        { id: 9, title: '用户增长策略与案例分析', category: '运营', status: 0, views: 934, createTime: '2024-01-07 09:45:00' },
        { id: 10, title: 'UI 设计中的色彩心理学', category: '设计', status: 1, views: 1987, createTime: '2024-01-06 14:10:00' },
      ]

      let filteredData = allData
      if (query?.keyword) {
        filteredData = filteredData.filter(item => item.title.includes(query.keyword!))
      }
      if (query?.status !== undefined && query?.status !== null) {
        filteredData = filteredData.filter(item => item.status === query.status)
      }

      const start = (page - 1) * pageSize
      const end = start + pageSize
      const data = filteredData.slice(start, end)

      return {
        code: 200,
        message: 'success',
        data: {
          list: data,
          total: filteredData.length,
          page,
          pageSize,
        },
      }
    },
  },
  {
    url: '/api/examples/detail',
    method: 'get',
    timeout: 500,
    response: ({ query }: { query: { id: number } }) => {
      const detailData: Record<number, any> = {
        1: { id: 1, title: '示例文章标题一', category: '技术', status: 1, views: 1234, createTime: '2024-01-15 10:30:00', content: '这是一篇技术文章的内容...' },
        2: { id: 2, title: '示例文章标题二', category: '产品', status: 1, views: 856, createTime: '2024-01-14 14:20:00', content: '这是一篇产品文章的内容...' },
        3: { id: 3, title: '示例文章标题三', category: '运营', status: 0, views: 423, createTime: '2024-01-13 09:15:00', content: '这是一篇运营文章的内容...' },
        4: { id: 4, title: '示例文章标题四', category: '设计', status: 1, views: 2156, createTime: '2024-01-12 16:45:00', content: '这是一篇设计文章的内容...' },
        5: { id: 5, title: '示例文章标题五', category: '市场', status: 1, views: 789, createTime: '2024-01-11 11:30:00', content: '这是一篇市场文章的内容...' },
      }
      const id = Number(query?.id)
      return {
        code: 200,
        message: 'success',
        data: detailData[id] || detailData[1],
      }
    },
  },
  {
    url: '/api/examples/create',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: any }) => {
      return {
        code: 200,
        message: '创建成功',
        data: { id: Math.floor(Math.random() * 10000), ...body },
      }
    },
  },
  {
    url: '/api/examples/update',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: any }) => {
      return {
        code: 200,
        message: '更新成功',
        data: body,
      }
    },
  },
  {
    url: '/api/examples/delete',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: { id: number } }) => {
      return {
        code: 200,
        message: '删除成功',
        data: { id: body.id },
      }
    },
  },
] as MockMethod[]
