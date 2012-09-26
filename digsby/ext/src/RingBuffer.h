#ifndef RingBuffer_h
#define RingBuffer_h

#include "Noncopyable.h"

template<typename T, int BufferSize>
class RingBuffer : Noncopyable
{ 
private: 
    T m_buffer[BufferSize]; 
    int m_index; 
    size_t m_size;

public: 
    RingBuffer() 
        : m_index(-1)
        , m_size(0)
    {} 

    ~RingBuffer()
    {
    } 

    void append(const T& value)
    {
        if (++m_index >= BufferSize)
            m_index = 0;
        m_buffer[m_index] = value;
        if (++m_size > BufferSize) m_size = BufferSize;
    } 

    /**
     * Copies this RingBuffer's data into buffer as one contiguous block, in
     * the "right" order. buffer will be filled with (and must be allocated
     * with enough length to hold) this->size() items.
     */
    void data(const T* buffer)
    {
        if (m_size < BufferSize)
            memcpy((void*)buffer, &m_buffer, sizeof(T) * m_size);
        else {
            size_t next = m_index + 1;
            if (next >= BufferSize)
                next = 0;

            const size_t numAfterNext = BufferSize - next;
            memcpy((void*)buffer, &m_buffer[next], numAfterNext * sizeof(T));
            memcpy((void*)(buffer + numAfterNext), &m_buffer, next * sizeof(T));
        }
    }

    size_t index() const { return m_index; } 
    int bufferSize() const { return BufferSize; }
    size_t size() const { return m_size; }
}; 

#endif // RingBuffer_h

